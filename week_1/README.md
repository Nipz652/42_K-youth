# Project Description

- This project implements a simplified Medallion Architecture pipeline (from Bronze Tier to QA inspector) for job postings scraped from a Job Search Engine. It demonstrates ETL concepts, data quality enforcement, and orchestration in Python

# Setup Instructions

**Prerequisites:** Python version 3.14

**Dependencies:** beautifulsoup4, pydantic, sqlite3

# Project Structure

```text
week1/
├── data/
│   ├── 0_source/          # Vendor Data: Unedited MHTML
│   │   ├── <TITLE_0>.mhtml
│   │   └── <TITLE_1>.mhtml
│   │
│   ├── 1_bronze/          # Raw Data: Decoded HTML
│   │   ├── <TITLE_0>.html
│   │   └── <TITLE_1>.html
│   │
│   ├── 2_silver/          # Clean Data: Removed HTML tags
│   │   ├── <TITLE_0>.json
│   │   └── <TITLE_1>.json
│   │
│   └── 3_gold/            # Final Warehouse: SQLite DB
│       └── jobs.db
│
├── src/
│   ├── ingestor.py        # Day 1: Extracts to data/1_bronze/
│   ├── processor.py       # Day 2: Cleans/Validates to data/2_silver/
│   ├── loader.py          # Day 3: Loads to data/3_gold/
│   └── profiler.py        # Day 4: Quality checks on Gold layer
│
├── main.py                # CLI Orchestrator (The Conductor)
├── pyproject.toml         # Environment & Dependencies (using uv)
├── uv.lock
└── README.md
```

# Usage

```text
python main.py ingest   # Extract raw HTML from MHTML
python main.py process  # Clean HTML → JSON
python main.py load     # Load JSON → SQLite DB
python main.py profile  # Run data quality checks
python main.py all      # Run full pipeline
```

## Implementation and Reflections

# Module 1: The Extractor (Bronze Tier)
Keeping raw HTML files is like keeping the “original evidence.” If later transformations introduce bugs or miss fields, you can always re‑process from the raw source. It makes debugging easier and ensures reproducibility.

# Module 2: Treatment Plant (Silver Tier)
Cloud systems prefer ELT because storage is cheap and scalable. Loading raw data first ensures nothing is lost. Sequential ETL can be slow — if one file fails, the whole run stalls. Distributed systems like Spark process thousands of files in parallel, reducing bottlenecks.

# Module 3: The Blueprint & The Vault (Gold Tier)
If job_title disappears, failing early prevents bad data from polluting analytics. Dashboards break if they rely on complete fields. INSERT OR IGNORE enforces idempotency — duplicates don’t accumulate, keeping the warehouse clean.

# Module 4: The QA Inspector & Orchestrator (QA inspector)
 If processor.py crashes halfway, manual reruns may duplicate or skip records. Tools like Airflow handle retries, scheduling, and dependencies automatically, making pipelines more reliable and production‑ready.
