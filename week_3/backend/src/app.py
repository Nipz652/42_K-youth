import asyncio
import os
import sys
import tempfile
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# ── Add week_2 folder to path so we can import find_skil_gaps ──────────
WEEK2_DIR = Path(__file__).parent / "week_2"
sys.path.insert(0, str(WEEK2_DIR))

from find_skil_gaps import find_skill_gaps, SkillGapResult  # noqa: E402

# ── App setup ───────────────────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DB_URL", "week_2/resources/jobs_d1.db")


# ── Health check ────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


# ── Chat endpoint ────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(request: Request):
    """
    Accepts JSON:
    {
        "message": "user text",
        "pdf_text": "extracted PDF text or null"
    }

    Returns:
    {
        "reply": "skill gap analysis result"
    }
    """
    # Parse body
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    message: str = body.get("message", "").strip()
    pdf_text: str | None = body.get("pdf_text", None)

    if not message and not pdf_text:
        return JSONResponse(
            status_code=400,
            content={"error": "No message or PDF text provided"}
        )

    # Use PDF text if uploaded, otherwise treat the message as resume content
    resume_text = pdf_text if pdf_text else message

    # Write to temp file — find_skill_gaps expects a file path
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8"
        ) as tmp:
            tmp.write(resume_text)
            tmp_path = tmp.name

        # Call week 2 function (it runs its own asyncio.run internally)
        result: SkillGapResult = find_skill_gaps(tmp_path, DB_URL)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {str(e)}"}
        )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ── Format reply ────────────────────────────────────────────────────
    if not result.gaps:
        reply = (
            "Great news! No skill gaps found — "
            "your profile matches the job requirements well."
        )
    else:
        # Top 5 most demanded gap skills
        top_skills = sorted(
            result.skill_demand.items(),
            key=lambda x: -x[1]
        )[:5]

        top_str = ", ".join(
            f"{skill} ({count} job{'s' if count > 1 else ''})"
            for skill, count in top_skills
        )

        reply = (
            f"I found {len(result.gaps)} skill gap(s) based on current job listings.\n\n"
            f"Missing skills: {', '.join(result.gaps)}\n\n"
            f"Most in-demand gaps: {top_str}\n\n"
            f"Most wanted: {result.most_wanted}\n"
            f"Demand range: {result.demand_range}"
        )

    return JSONResponse(content={"reply": reply})


# ── Database visualisation endpoints (Bonus) ─────────────────────────
import sqlite3

def get_db():
    return sqlite3.connect(DB_URL)

@app.get("/api/stats/tech-distribution")
def tech_distribution():
    """Returns skill -> job count for pie chart."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != ''"
        )
        rows = cursor.fetchall()
        conn.close()

        demand: dict = {}
        for (stack,) in rows:
            for skill in stack.split(","):
                skill = skill.strip().lower()
                if skill and skill not in {"not specified", "n/a", "none"}:
                    demand[skill] = demand.get(skill, 0) + 1

        # Return top 10 for readability
        top = sorted(demand.items(), key=lambda x: -x[1])[:10]
        return JSONResponse(content={
            "labels": [k for k, v in top],
            "values": [v for k, v in top],
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats/jobs-per-source")
def jobs_per_source():
    """Returns job count — used for bar chart."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Count tagged vs untagged
        cursor.execute("""
            SELECT
                CASE
                    WHEN tech_stack IS NULL OR tech_stack = '' THEN 'Untagged'
                    ELSE 'Tagged'
                END as status,
                COUNT(*) as count
            FROM jobs
            GROUP BY status
        """)
        rows = cursor.fetchall()
        conn.close()
        return JSONResponse(content={
            "labels": [r[0] for r in rows],
            "values": [r[1] for r in rows],
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/jobs/search")
def search_jobs(q: str = ""):
    """Search jobs by keyword in description or tech_stack."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        like = f"%{q}%"
        cursor.execute("""
            SELECT source_id, tech_stack, description
            FROM jobs
            WHERE tech_stack LIKE ? OR description LIKE ?
            LIMIT 20
        """, (like, like))
        rows = cursor.fetchall()
        conn.close()
        return JSONResponse(content={
            "results": [
                {
                    "source_id": r[0],
                    "tech_stack": r[1],
                    "description": r[2][:200] + "..." if r[2] and len(r[2]) > 200 else r[2],
                }
                for r in rows
            ]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})