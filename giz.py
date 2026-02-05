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
from pathlib import Path

from playwright.sync_api import sync_playwright # for browser automation
from rich import print


# (2) This function fixes the date format to be consistent because the website has dates in different formats which is annoying
def normalize_date(date: str) -> str:
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


# (5) Start playwright; this is what controls the browser
def main():
    
    # Some of the reports didnt download and I cant figure out why. So I wanted an overview of the faiiled downloads
    failed_downloads = []

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
            user_data_dir=user_data_dir, headless=True, accept_downloads=True 
        )            # headless=True means no browser window shows up
                     # accept_downloads=True allows downloading files

        ## Navigate the browser. Bascially try-and-error here. I went through the website manually and
        ## then instructed playwright what to do
        page = browser_context.pages[0]  # Get the default page

        # Go to the GIZ publications website
        print("Navigating to website...")
        page.goto("https://publikationen.giz.de/esearcha/browse.tt.html")
        page.wait_for_load_state("networkidle") # Need to wait, such that the page is fully loaded

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
        page.wait_for_timeout(30_000)

        # Switch to full view instead of short view. This shows more details for each result
        page.click("button:has-text('Kurzanzeige')")
        page.click("li:has-text('Vollanzeige')")
        page.wait_for_timeout(120_000)

        # Setup JSON file to save metadata from project overviews
        results_file = Path("results_giz.json")
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                results = json.load(f)
        else:
            results = []
        

        # Find the container with all the results
        container = page.locator("#results-container")
        # Get all the result items
        all_items = container.locator(".row.efxRecordRepeater").all()
        # Add a counter to the downloads to gain a better overview of the progress
        total_reports = len(all_items)
        print(f"Found {total_reports} total reports")
        
        # Counter to track progress
        current_report = 0

        # Loop through each result item
        for item in all_items:
            current_report += 1  # increment counter for each report
            print(f"\n--- Processing report {current_report} of {total_reports} ---")
            
            random_delay(2, 4)  # wait randomly between 1-3 seconds

            # Some reports didnt have links, so I needed to skip them
            if item.locator(".shortsummary-url a").count() == 0:
                continue
            slug_element = item.locator(".shortsummary-url a").first
            slug = slug_element.get_attribute("alt").split(" ")[0]

            # Skips if we already downloaded this one
            metadata = next((r for r in results if r["slug"] == slug), None)
            if metadata:
                if Path(pdf_dir / metadata["filename"]).exists():
                    print(f"Skipping {slug[:30]}... because it already exists")
                    continue
            
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
            lang = metadata["Sprache"][:2]
            metadata["slug"] = slug # Learned something: Slug is a URL-friendly version of a string, typically used for creating clean, readable URLs or identifiers.
            filename = f"{date}_{id}_{lang}.pdf".lower()
            metadata["filename"] = filename
            download_url = rows[-1].locator("a").first.get_attribute("href")
            # Add metadata if its new
            if metadata not in results:
                results.append(metadata)
            # Save results, so if the script crashes not everything will be lost
            with results_file.open("w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            print(f"Downloading ({current_report}/{total_reports}):\t{filename}")

            try:
                # Add small delay before download
                random_delay(1.5, 3)
                # Create a new page for each download to avoid issues with the main page
                download_page = browser_context.new_page()
                # Set up the download handler before navigating
                with download_page.expect_download(timeout=30000) as download_info:
                    # Instead of direct navigation, use click on a new tab
                    download_page.evaluate("(url) => window.location.href = url", download_url)
                download = download_info.value
                path = pdf_dir / filename
                download.save_as(path)
                print(f"Saved ({current_report}/{total_reports}):\t{filename}")
                download_page.close()
            # If something goes wrong, print error and continue
            except Exception as e:
                print(f"Error downloading {filename}: {e}")
                
            # Plus add failed download to my created list
                failed_downloads.append({
                        "project_number": id,
                        "filename": filename,
                        "slug": slug,
                        "title": metadata.get("Titel", ""),
                        "date": metadata.get("Erscheinungsdatum", ""),
                        "url": metadata.get("url", ""),
                        "download_url": download_url,
                        "error": str(e)
                    })
            continue
            random_delay(6, 10)

        browser_context.close()
        print("Browser closed.")

# (6) Since not all reports were downloadbale, I want an overview of the failed downloads for colleagues to cross check
# Export failed downloads to CSV
    if failed_downloads:
            print(f"\n{'='*60}")
            print(f"FAILED DOWNLOADS SUMMARY")
            print(f"{'='*60}")
            print(f"Total failed downloads: {len(failed_downloads)}")
            print(f"Percentage: {len(failed_downloads) / total_reports * 100:.2f}%")
            
            # Convert list to df
            df_failed = pd.DataFrame(failed_downloads)

            # Export to csv
            df_failed.to_csv("pdfs\failed_downloads.csv", index=False, encoding="utf-8")

            print(f"Failed downloads exported to: {"pdfs\failed_downloads.csv"}")
    else:
            print("\n✓ All downloads successful! No failed downloads to report.")


if __name__ == "__main__":
    main()
