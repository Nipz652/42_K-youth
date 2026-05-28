import os
import sys
import sqlite3
import tempfile
from pathlib import Path

# ── Add week_2 to path before any local imports ─────────────────────────
WEEK2_DIR = Path(__file__).parent / "week_2"
sys.path.insert(0, str(WEEK2_DIR))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from google import genai
from find_skil_gaps import _find_skill_gaps_async, SkillGapResult, DailyQuotaExceededError

load_dotenv()

# ── App setup ────────────────────────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DB_URL", "src/week_2/resources/jobs_d1.db")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ── Keyword detection — triggers skill gap analysis ──────────────────────
SKILL_GAP_KEYWORDS = [
    "skill gap", "skill gaps", "missing skills", "find skills",
    "what skills", "skills i need", "skills needed", "skills required",
    "analyse my resume", "analyze my resume", "evaluate my resume",
    "review my resume", "check my resume", "assess my resume",
]

def wants_skill_gap(message: str) -> bool:
    lower = message.lower()
    return any(keyword in lower for keyword in SKILL_GAP_KEYWORDS)


# ── General Gemini chat ──────────────────────────────────────────────────
async def general_chat(message: str, pdf_text: str | None) -> str:
    """
    Uses Gemini as a general conversational assistant.
    If a PDF is attached, it is included as context.
    """
    client = genai.Client(api_key=GOOGLE_API_KEY)

    if pdf_text:
        contents = (
            f"The user has shared the following resume:\n\n"
            f"{pdf_text}\n\n"
            f"User message: {message}"
        )
    else:
        contents = message

    response = await client.aio.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=contents,
    )
    return response.text.strip()


# ── Health check ─────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


# ── Chat endpoint ─────────────────────────────────────────────────────────
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
        "reply": "response string"
    }

    If the message contains skill gap keywords AND a PDF is attached,
    runs the full skill gap analysis from Week 2.
    Otherwise, uses Gemini as a general conversational assistant.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    message: str = body.get("message", "").strip()
    pdf_text: str | None = body.get("pdf_text", None)

    if not message and not pdf_text:
        return JSONResponse(
            status_code=400,
            content={"error": "No message or PDF provided"}
        )

    print(f"Received message: '{message[:100]}'")
    print(f"PDF text present: {pdf_text is not None}")

    # ── Decide: skill gap analysis or general chat ───────────────────────
    if wants_skill_gap(message) and pdf_text:
        # Run full Week 2 skill gap analysis
        print("Mode: skill gap analysis")
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(pdf_text)
                tmp_path = tmp.name

            result: SkillGapResult = await _find_skill_gaps_async(tmp_path, DB_URL)

        except DailyQuotaExceededError as e:
            return JSONResponse(
                status_code=429,
                content={"error": str(e)}
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={"error": f"Skill gap analysis failed: {str(e)}"}
            )
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        if not result.gaps:
            reply = (
                "Great news! No skill gaps found — "
                "your profile matches the job requirements well."
            )
        else:
            top_skills = sorted(
                result.skill_demand.items(), key=lambda x: -x[1]
            )[:5]
            top_str = ", ".join(
                f"{s} ({c} job{'s' if c > 1 else ''})"
                for s, c in top_skills
            )
            gaps_str = " - ".join(result.gaps)
            reply = (
                f"Skills gap identified: - {gaps_str}\n\n"
                f"Most in-demand missing skills: {top_str}\n\n"
                f"Most wanted: {result.most_wanted}"
            )

    else:
        # General Gemini conversation
        print("Mode: general chat")
        try:
            reply = await general_chat(message, pdf_text)
        except DailyQuotaExceededError as e:
            return JSONResponse(
                status_code=429,
                content={"error": str(e)}
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={"error": f"Chat failed: {str(e)}"}
            )

    return JSONResponse(content={"reply": reply})


# ── Database visualisation endpoints ─────────────────────────────────────
def get_db():
    return sqlite3.connect(DB_URL)


@app.get("/api/stats/tech-distribution")
def tech_distribution():
    """Returns skill -> job count for pie chart."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tech_stack FROM jobs "
            "WHERE tech_stack IS NOT NULL AND tech_stack != ''"
        )
        rows = cursor.fetchall()
        conn.close()

        demand: dict = {}
        for (stack,) in rows:
            for skill in stack.split(","):
                skill = skill.strip().lower()
                if skill and skill not in {"not specified", "n/a", "none"}:
                    demand[skill] = demand.get(skill, 0) + 1

        top = sorted(demand.items(), key=lambda x: -x[1])[:10]
        return JSONResponse(content={
            "labels": [k for k, v in top],
            "values": [v for k, v in top],
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats/jobs-per-source")
def jobs_per_source():
    """Returns tagged vs untagged job counts for bar chart."""
    try:
        conn = get_db()
        cursor = conn.cursor()
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
                    "description": (
                        r[2][:200] + "..."
                        if r[2] and len(r[2]) > 200
                        else r[2]
                    ),
                }
                for r in rows
            ]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})