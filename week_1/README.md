## Implementation and Reflections

# Module 1: The Extractor (Bronze Tier)
Keeping raw HTML files is like keeping the “original evidence.” If later transformations introduce bugs or miss fields, you can always re‑process from the raw source. It makes debugging easier and ensures reproducibility.

# Module 2: Treatment Plant (Silver Tier)
Cloud systems prefer ELT because storage is cheap and scalable. Loading raw data first ensures nothing is lost. Sequential ETL can be slow — if one file fails, the whole run stalls. Distributed systems like Spark process thousands of files in parallel, reducing bottlenecks.

# Module 3: The Blueprint & The Vault (Gold Tier)
If job_title disappears, failing early prevents bad data from polluting analytics. Dashboards break if they rely on complete fields. INSERT OR IGNORE enforces idempotency — duplicates don’t accumulate, keeping the warehouse clean.

# Module 4: The QA Inspector & Orchestrator (QA inspector)
 If processor.py crashes halfway, manual reruns may duplicate or skip records. Tools like Airflow handle retries, scheduling, and dependencies automatically, making pipelines more reliable and production‑ready.