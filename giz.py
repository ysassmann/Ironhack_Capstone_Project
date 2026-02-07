#!/usr/bin/env python3

### This is a script to download PDF files from the GIZ website to gather my database
### The idea here was to download all reports and scrape metadata based on the project descriptions given in the short summary
### I've previous experience in WebScraping in R. I tried to scrape the documents using HTML.
### However, as I want to download the pdfs, rather than the contents of the website, I didn't get far with HTML. 
### I thus came across playwrith and uv for controlling the browser, read into and played around with it.


# (1) Load necessary packages
import pandas as pd
import json
import os
import re
import tempfile
import time
import random
import shutil
from pathlib import Path
from datetime import datetime, timedelta


from playwright.sync_api import sync_playwright # for browser automation
from playwright.sync_api import TimeoutError
from rich import print


# (2) This function fixes the date format to be consistent because the website has dates in different formats which is annoying
def normalize_date(date: str) -> str:
    """Standardize date formats from details of reports to YYYY-MM"""
    if m := re.match(r'^(\d{2})\.(\d{4})$', date):  # MM.YYYY
        return f"{m.group(2)}-{m.group(1)}"
    if m := re.match(r'^(\d{4})\.(\d{2})$', date):  # YYYY.MM
        return f"{m.group(1)}-{m.group(2)}"
    if m := re.match(r'^(\d{4})-(\d{2})$', date):   # YYYY-MM (already correct)
        return date
    if m := re.match(r'^(\d{4})$', date):           # YYYY only
        return date
    return date  # fallback

# (3) This function adds random delays, mimincing more human-like behavior to deter automatic scraping protection of the website
def random_delay(min_seconds=2, max_seconds=5):
    """Add a random delay to mimic human behavior"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

# (4) Create the folder where PDFs will be saved
pdf_dir = Path("pdfs") / "giz" # Path("pdfs") creates a Path object for the pdfs folder + / "giz" adds another folder inside it
pdf_dir.mkdir(parents=True, exist_ok=True) # make the folders if they don't exist


## I ran into issues with the website after 1 hour or roughly 400 scripts, so I had to devide the sessions into smaller chunks.
# (5) Progress tracking
def save_progress(report_index):
    """Save the current progress"""
    progress_file = Path("download_progress.json")
    with progress_file.open("w", encoding="utf-8") as f:
        json.dump({"last_completed_index": report_index, "timestamp": datetime.now().isoformat()}, f)

def load_progress():
    """Load the last progress"""
    progress_file = Path("download_progress.json")
    if progress_file.exists():
        with progress_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"📍 Resuming from report {data['last_completed_index'] + 1}")
            return data['last_completed_index']
    return -1  # Start from beginning

def should_restart_session(downloads_in_session, session_start_time, max_downloads=350, max_minutes=45):
    """Check if we should restart the browser session"""
    elapsed = datetime.now() - session_start_time
    if downloads_in_session >= max_downloads:
        print(f"⚠️ Reached {downloads_in_session} downloads - restarting session")
        return True
    if elapsed > timedelta(minutes=max_minutes):
        print(f"⚠️ Session running for {elapsed.seconds // 60} minutes - restarting session")
        return True
    return False


# (6) Start playwright; this is what controls the browser
def scrape_with_session(start_index=0):
    """Run scraping session starting from given index"""
    
    # Some of the reports didnt download and I cant figure out why. So I wanted an overview of the failed downloads
    failed_file = Path("failed_downloads.json")
    failed_downloads = json.load(failed_file.open("r", encoding="utf-8")) if failed_file.exists() else []
    results_file = Path("results_giz.json")
    results = json.load(results_file.open("r", encoding="utf-8")) if results_file.exists() else []

    # Session tracking
    downloads_in_session = 0
    session_start_time = datetime.now()
    consecutive_timeouts = 0
    MAX_CONSECUTIVE_TIMEOUTS = 5

    with sync_playwright() as p:
        # Create temporary directory for browser profile
        # I had to do this to make PDFs download instead of opening in browser
        tmp_dir = tempfile.mkdtemp() # makes a temp folder
        user_data_dir = os.path.join(tmp_dir, "userdir") # path for user data
        default_dir = os.path.join(user_data_dir, "Default") # default profile folder
        os.makedirs(default_dir, exist_ok=True) # create it

        # Set preferences to always open PDF externally
        # This took me forever to figure out. Needed help from a co-worker but this setting makes PDFs downloadable
        default_preferences = {"plugins": {"always_open_pdf_externally": True}}

        # Write preferences to file. The browser reads this file to know what settings to use
        with open(os.path.join(default_dir, "Preferences"), "w", encoding="utf-8") as f:
            json.dump(default_preferences, f)

        # Launch persistent context with the configured user data directory
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir, headless=False, accept_downloads=True
        )            # headless=True means no browser window shows up
                     # accept_downloads=True allows downloading files

        ## Navigate the browser. Bascially try-and-error here. I went through the website manually and
        ## then instructed playwright what to do
        page = browser_context.pages[0]  # Get the default page

        # Go to the GIZ publications website
        print("Navigating to website...")
        page.goto("https://publikationen.giz.de/esearcha/browse.tt.html")
        page.wait_for_load_state("networkidle") # Wait until the page is fully loaded

        # Search for the document type "Evaluierungsberichte" that I am interested in
        print("Searching for Evaluierungsberichte...")
        page.click("text=Suche starten")
        page.wait_for_load_state("networkidle")
        page.click("li:has-text('Projektevaluierung')")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5_000)
        
        # This was helpful: you can display all search results in one page, so you dont have to iterate through the pages
        print("Opening results per page dropdown...")
        page.click("button.multiselect.dropdown-toggle[data-toggle='dropdown']")
        page.wait_for_timeout(1000)

        print("Selecting 'Alles auf einer Seite'...")
        page.click("ul.multiselect-container li:has-text('Alles auf einer Seite')")
        page.wait_for_load_state("networkidle")

        # Switch to full view instead of short view. This shows more details for each result
        page.click("button:has-text('Kurzanzeige')")
        page.click("li:has-text('Vollanzeige')")
        page.wait_for_timeout(120_000)

        # Find the container with all the results
        container = page.locator("#results-container")
        # Get all the result items
        all_items = container.locator(".row.efxRecordRepeater").all()
        # Add a counter to the downloads to gain a better overview of the progress
        total_reports = len(all_items)
        print(f"Found {total_reports} total reports")

        # Save total count to file for later reference
        total_file = Path("total_reports.json")
        with total_file.open("w", encoding="utf-8") as f:
            json.dump({"total_reports": total_reports}, f) 

        # Process items, starting from start_index
        for idx, item in enumerate(reversed(all_items)):
            # Skip items before start_index
            if idx <= start_index:
                continue

            current_report = idx + 1
            print(f"\n--- Processing report {current_report} of {total_reports} ---")
            
            # Check if we should restart session
            if should_restart_session(downloads_in_session, session_start_time):
                print("💫 Restarting browser session...")
                save_progress(idx - 1)  # Save before restarting
                browser_context.close()
                try:
                    shutil.rmtree(tmp_dir)
                except Exception as e:
                    print(f"Warning: temp dir cleanup failed: {e}")
                return idx - 1  # Return index to resume from

            # Check for consecutive timeouts
            if consecutive_timeouts >= MAX_CONSECUTIVE_TIMEOUTS:
                print(f"❌ {MAX_CONSECUTIVE_TIMEOUTS} consecutive timeouts - saving progress and restarting session")
                save_progress(idx - consecutive_timeouts - 1)  # Save last successful
                browser_context.close()
                try:
                    shutil.rmtree(tmp_dir)
                except Exception as e:
                    print(f"Warning: temp dir cleanup failed: {e}")
                return idx - consecutive_timeouts - 1

            if item.locator(".shortsummary-url a").count() == 0:
                continue
            
            slug_element = item.locator(".shortsummary-url a").first
            slug = slug_element.get_attribute("alt").split(" ")[0]
            
            # Get all the metadata from the summary view. Had some help with claude for the generalisation of the regex patterns.
            detail_container = item.locator(".tab-pane")
            rows = detail_container.locator(".row").all()
            metadata = {}
            for row in rows:
                divs = row.locator("div").all()
                if len(divs) >= 2:
                    metadata[divs[0].inner_text(timeout=5000)] = divs[1].inner_text(timeout=5000)
            metadata["url"] = rows[0].locator("a").first.get_attribute("href")
            id = re.search(r"Projektnummer: ((\d|\.)+)", metadata.get("Weitere Nummern", ""))
            id = id.group(1) if id else "unknown"
            metadata["id"] = id
            date = normalize_date(metadata["Erscheinungsdatum"]) # Use the function we created above
            lang = metadata.get("Sprache", "xx").strip()[:2].lower()
            metadata["slug"] = slug # Learned something: Slug is a URL-friendly version of a string, typically used for creating clean, readable URLs or identifiers.
            filename = f"{date}_{id}_{lang}.pdf".lower()
            metadata["filename"] = filename

            # Find download link AND extract size - search in the ENTIRE item
            download_url = None
            remote_size_bytes = None
            download_link_element = None

            # Look through ALL links in the entire item (not just detail_container)
            all_links = item.locator("a").all()
            for link in all_links:
                href = link.get_attribute("href")
                if href and href.lower().endswith(".pdf"):
                    download_url = href
                    
                    # Try to get size from the link text
                    link_text = link.inner_text()
                    size_match = re.search(r'(\d+)\s*KB', link_text, re.IGNORECASE)
                    if size_match:
                        size_kb = int(size_match.group(1))
                        remote_size_bytes = size_kb * 1024
                        download_link_element = link  # save this exact link for download
                        print(f"✓ Found size in link: {remote_size_bytes} bytes ({size_kb} KB)")
                        break

            # If we didn't find the size in the link, look in the entire item text
            if download_url and not remote_size_bytes:
                item_text = item.inner_text()
                size_match = re.search(r'(\d+)\s*KB', item_text, re.IGNORECASE)
                if size_match:
                    size_kb = int(size_match.group(1))
                    remote_size_bytes = size_kb * 1024
                    print(f"✓ Found size in item text: {remote_size_bytes} bytes ({size_kb} KB)")

            if not download_url:
                print(f"No PDF download link for project {id}, skipping...")
                failed_downloads.append({
                    "project_number": id,
                    "filename": filename,
                    "slug": slug,
                    "title": metadata.get("Titel", ""),
                    "date": metadata.get("Erscheinungsdatum", ""),
                    "url": metadata.get("url", ""),
                    "download_url": None,
                    "error": "No PDF download link found"
                })
                # Save immediately
                with failed_file.open("w", encoding="utf-8") as f:
                    json.dump(failed_downloads, f, indent=2, ensure_ascii=False)
                continue

            # I ran into the issue that the scraper would download summary reports and didnt download any other reports if the project number and language already existed
            # But I need the comprehensive reports (100+ pages). So I want to replace the old report, with the more comprehensive report, if the file size is bigger, while keeping the language constant
            # Check for existing files with same project number and language
            existing_files = list(pdf_dir.glob(f"*_{id}_{lang}.pdf"))
            should_download = True
            existing_file = None

            if existing_files:
                existing_file = max(existing_files, key=lambda p: p.stat().st_size)
                print(f"Found existing file for project {id} in {lang}: {existing_file.name} ({existing_file.stat().st_size} bytes)")
                
                # Compare with remote size if we have it
                if remote_size_bytes:
                    if remote_size_bytes <= existing_file.stat().st_size:
                        print(f"✓ Existing file is same or bigger ({existing_file.stat().st_size} >= {remote_size_bytes}) → skip download")
                        should_download = False
                    else:
                        print(f"📥 Remote file is bigger ({remote_size_bytes} > {existing_file.stat().st_size}) → will download and replace")
                else:
                    print(f"⚠️ Could not determine remote file size from link, will download to be safe")
            else:
                print(f"No existing file found for project {id} in {lang}, will download")

            if should_download:
                print(f"Downloading ({current_report}/{total_reports}):\t{filename}")
                path = pdf_dir / filename

                if not download_link_element:
                    print(f"❌ Could not find PDF link for download, skipping")
                    continue

                try:
                    # Capture the actual PDF response when clicking the download link
                    with page.expect_download(timeout=60000) as download_info:
                        download_link_element.click()

                    download = download_info.value
                    download.save_as(path)
                    print(f"✅ Downloaded via Playwright: {filename}")

                    # Success - reset timeout counter and increment download counter
                    consecutive_timeouts = 0
                    downloads_in_session += 1

                except TimeoutError:
                    print(f"❌ Timeout while trying to download {filename}")
                    consecutive_timeouts += 1
                    print(f"⚠️ Consecutive timeouts: {consecutive_timeouts}/{MAX_CONSECUTIVE_TIMEOUTS}")

                    failed_downloads.append({
                        "project_number": id,
                        "filename": filename,
                        "slug": slug,
                        "title": metadata.get("Titel", ""),
                        "date": metadata.get("Erscheinungsdatum", ""),
                        "url": metadata.get("url", ""),
                        "download_url": download_url,
                        "error": "Playwright download timeout"
                    })
                    with failed_file.open("w", encoding="utf-8") as f:
                        json.dump(failed_downloads, f, indent=2, ensure_ascii=False)
                    continue

                # Remove old file if replaced
                if existing_file and existing_file.exists() and existing_file.name != path.name:
                    existing_file.unlink()
                    results = [r for r in results if r.get("filename") != existing_file.name]

                # Save metadata
                if not any(r.get("filename") == filename for r in results):
                    results.append(metadata)

                with results_file.open("w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)

                # Save progress periodically
                if downloads_in_session % 10 == 0:
                    save_progress(idx)

            else:
                print(f"⏭️ Processed ({current_report}/{total_reports}):\t{filename}")
            
        browser_context.close()

        # Temporary Chromium profile is removed after each run.
        try:
            shutil.rmtree(tmp_dir)
        except Exception as e:
            print(f"Warning: temp dir cleanup failed: {e}")

        print("Browser closed.")
        return total_reports - 1

# (8) Restart where left off
def main():
    """Main function with automatic resume and restart"""
    print("="*60)
    print("GIZ PDF Scraper with Auto-Restart")
    print("="*60)
    
    start_index = load_progress()
    
    while True:
        last_index = scrape_with_session(start_index)
        
        # Check if we're done
        if last_index >= 1344:  # Adjust based on total reports
            print("\n" + "="*60)
            print("✅ ALL REPORTS PROCESSED!")
            print("="*60)
            break
        
        # Resume from where we left off
        start_index = last_index
        print(f"\n🔄 Resuming from report {start_index + 1}...")
        time.sleep(5)  # Brief pause before restarting

# (9) Since not all reports were downloadable, I want an overview of the failed downloads for colleagues to cross check
# Export failed downloads to CSV
    failed_file = Path("failed_downloads.json")
    total_file = Path("total_reports.json")
    
    if failed_file.exists():
        failed_downloads = json.load(failed_file.open("r", encoding="utf-8"))
        if failed_downloads:
            print(f"\n{'='*60}")
            print(f"FAILED DOWNLOADS SUMMARY")
            print(f"{'='*60}")
            print(f"Total failed downloads: {len(failed_downloads)}")
            
            # Load total from saved file
            if total_file.exists():
                total_reports = json.load(total_file.open("r", encoding="utf-8"))["total_reports"]
                print(f"Percentage: {len(failed_downloads) / total_reports * 100:.2f}%")
            
            # Already saved as JSON throughout, just confirm
            print(f"Failed downloads saved to: failed_downloads.json")
            
            # OPTIONAL: Also export to CSV for easy viewing in Excel
            df_failed = pd.DataFrame(failed_downloads)
            df_failed.to_csv("pdfs/failed_downloads.csv", index=False, encoding="utf-8")
            print(f"Also exported to CSV: pdfs/failed_downloads.csv")
        else:
            print("\n✓ All downloads successful! No failed downloads to report.")

if __name__ == "__main__":
    main()
