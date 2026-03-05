# EvidenceAI
### Evidence Chatbot for German Development Cooperation

> A RAG-based deep research agent that makes 1,200+ GIZ project evaluation reports instantly searchable and queryable — enabling evidence-based decision-making in development cooperation.

---

## The Problem

Development cooperation generates enormous institutional knowledge: over 10,000 evaluation reports documenting what works, what fails, and why. In practice, this knowledge goes unused:

- Reports are too numerous and fragmented to search manually
- Institutional learning happens only sporadically
- New project proposals are designed without referencing past evidence
- Staff turnover erodes tacit knowledge permanently

The result: the same mistakes get repeated, and proven solutions go unnoticed.

---

## Solution

EvidenceAI is a Streamlit-based chat interface powered by a LangChain RAG agent. Users — typically ministry staff reviewing new project proposals — can ask complex, nuanced research questions in natural language and receive structured, evidence-grounded answers with source citations, across English, German, French, and Spanish.

**User story:** A ministry employee needs to review a new project proposal and cross-check it against existing evidence. Instead of manually searching hundreds of reports, they open EvidenceAI, ask their question, and get a structured analytical response in under 3 minutes.

---

## Architecture

```
Web Scraper (Playwright)
        │
        ▼
  ~1,200 PDF Reports (GIZ Publication Database)
        │
        ▼
  PDF Parsing + Text Chunking (LangChain / PyPDF)
        │
        ▼
  Vector Embeddings (OpenAI text-embedding-3-large via Azure)
        │
        ▼
  ChromaDB Vector Store (local or Azure-hosted)
        │
        ▼
  Deep Research Agent (GPT-5 via Azure + 8 specialist tools)
        │
        ▼
  Streamlit Frontend
```

---

## Dataset

| Metric | Value |
|---|---|
| Source | [GIZ Publications Database](https://publikationen.giz.de/esearcha/browse.tt.html) |
| Reports | 1,059 evaluation reports (2014–2025) |
| Pages | 37,654 |
| Embedded chunks | 115,752 |
| Tokens | ~82 million |
| Languages | EN, DE, FR, ES |
| Countries | 120+ |
| Sectors | 20+ |

Reports include three formats: summary reports, "At-a-Glance" briefs, and comprehensive evaluation reports (100+ pages). Where multiple formats existed for the same project, the scraper preferentially downloaded the larger (more comprehensive) file.

---

## Components

### 1. Web Scraper (`scraper.py`)
A Playwright-based browser automation script that navigates the GIZ publications portal, filters for project evaluations, and downloads all matching PDFs with metadata. Key features:
- Human-mimicking random delays
- Session restart logic (avoids bot detection after ~350 downloads)
- Resume-from-checkpoint support via `download_progress.json`
- Prefers comprehensive reports over summaries (compares file sizes before downloading)
- Exports failed downloads to `failed_downloads.json` for manual follow-up

### 2. Vector Store (`vectorstore.py`)
Processes downloaded PDFs into a searchable ChromaDB vector store:
- Splits documents into overlapping chunks (1,500 tokens, 300 overlap)
- Enriches each chunk with catalog metadata (title, keywords, classification, date, author) baked into the embedding
- Batched embedding with automatic resume on interruption
- Supports both local ChromaDB and remote Azure-hosted ChromaDB

### 3. Research Agent (`agent.py`)
A LangChain `AgentExecutor` powered by GPT-5, with 8 specialist retrieval tools:

| Tool | Purpose |
|---|---|
| `deep_search` | Multi-angle search with query variations in 3 languages |
| `search_documents` | Targeted single-query retrieval |
| `compare_projects` | Cross-context project comparison |
| `find_failure_cases` | Surfaces negative outcomes and failures |
| `find_longterm_outcomes` | Post-project sustainability findings |
| `analyze_context_factors` | Political economy and institutional factors |
| `identify_risk_patterns` | Early warning signs and red flags |
| `find_implementation_details` | HOW things were implemented |

The agent is capped at 4 tool calls per query to ensure fast response times (~1–3 minutes). The system prompt enforces strict evidence discipline: no claims without citations, explicit flagging of thin evidence, and no extrapolation across contexts.

### 4. Streamlit Frontend (`app.py`)
A dark-themed research interface with:
- Session management with persistent history (`research_history.json`)
- Follow-up questions with automatic context passing
- Tool call trace viewer
- Export to `.txt` and `.pdf` (ReportLab)
- Auto-connection to local or remote ChromaDB on startup

---

## Results

- **Deep Research Agent** capable of answering complex questions grounded exclusively in the GIZ corpus, across 4 languages
- **Radical reduction in analysis time**: evidence that previously required hours of manual searching is now accessible in minutes
- **Decision support**: structured analytical outputs with citations help ministry staff critically review project proposals against past experience
- **Institutional memory preservation**: tacit knowledge embedded in reports is now accessible independent of individual staff members

---

## Limitations & Next Steps

- **Public deployment blocked**: the vector database was successfully migrated to Azure Container Instances, but connecting Streamlit Cloud to the Azure-hosted ChromaDB failed. Currently runs only locally.
- **Next step**: migrate to a managed vector DB service (Pinecone or ChromaDB Cloud) to enable public sharing
- **Output quality**: agent responses need systematic evaluation; user feedback has not yet been formally validated
- **Coverage**: ~15% of reports could not be downloaded (scraping timeouts, missing PDFs); a manual follow-up list is available in `failed_downloads.json`

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set environment variables
cp .env.example .env
# Add OPENAI_AZURE_API_KEY, CHROMA_HOST (optional), CHROMA_PORT (optional)

# Step 1: Scrape PDFs
python scraper.py

# Step 2: Build vector store
python vectorstore.py

# Step 3: Launch app
streamlit run app.py
```

---

## Project Structure

```
├── scraper.py              # Playwright PDF downloader
├── vectorstore.py          # PDF → ChromaDB pipeline
├── agent.py                # Deep Research Agent
├── app.py                  # Streamlit frontend
├── pdfs/giz/               # Downloaded PDFs
├── chroma_db/              # Local vector store
├── results_giz.json        # Scraped metadata
├── failed_downloads.json   # Failed download log
└── research_history.json   # Session history
```

---

## Tech Stack

`Python` · `Playwright` · `LangChain` · `ChromaDB` · `OpenAI (Azure)` · `Streamlit` · `ReportLab`