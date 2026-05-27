# Resume Helper Chatbot — Week 3

A full-stack containerised chat application that analyses resume skill gaps using AI. Users upload their resume as a PDF, and the system compares their skills against a tagged job database from Week 2 to identify what skills the job market demands that they don't have yet.

---

## Project Overview

This project builds on the AI pipeline from Week 2 and wraps it in a production-ready web application:

- **Frontend** — A Bootstrap chat interface served by FastAPI and Jinja2, where users can type messages and upload PDF resumes
- **Backend** — A FastAPI REST server that receives user input, calls the Week 2 skill gap analysis functions, and returns results
- **Landing Page** — A static overview page explaining the full AI pipeline
- **Job Stats Dashboard** — Charts.js visualisations of job market data from the Week 1/2 database

All three services run as isolated Docker containers connected via a shared bridge network.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker Desktop | Latest | Run all services as containers |
| Docker Compose | Included with Docker Desktop | Orchestrate multi-container setup |
| Python | 3.12+ | Local development only (optional) |
| uv | Latest | Local dependency management (optional) |

Install Docker Desktop from: `https://www.docker.com/products/docker-desktop/`

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd week_3
```

### 2. Create the secrets file

Docker secrets are used to store the Google API key securely:

```bash
mkdir secrets
echo "your_actual_google_api_key_here" > secrets/google_api_key.txt
```

> **Never commit `secrets/google_api_key.txt` to Git.** It is listed in `.gitignore`.

Get your API key at: `https://aistudio.google.com/app/apikey`

### 3. Configure environment variables

Copy the example files and fill in your values:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

**`backend/.env`:**
```dotenv
GOOGLE_API_KEY=your_google_api_key_here
DB_URL=src/week_2/resources/jobs_d1.db
OLLAMA_HOST=http://localhost:11434
```

**`frontend/.env`:**
```dotenv
BACKEND_URL=http://localhost:8001
```

> When running with Docker Compose, `BACKEND_URL` should be `http://backend:8001` (service name, not localhost).

### 4. Place the Week 2 database

Make sure your tagged SQLite database is at:
```
backend/src/week_2/resources/jobs_d1.db
```

If it is not yet tagged, run the tagging script after starting the containers (see Usage).

---

## Usage

### Running with Docker Compose (recommended)

```bash
# Build images and start all services
docker compose up --build

# Run in background (detached mode)
docker compose up --build -d

# Check running containers
docker compose ps

# Stop all services
docker compose down
```

### First run only — tag the job database

```bash
docker exec -it week_3-backend-1 uv run python src/week_2/tag_data.py
```

### Accessing the services

| Service | URL | Description |
|---|---|---|
| Chatbot | `http://localhost:8000` | Main chat interface |
| Job Stats | `http://localhost:8000/stats` | Charts and search dashboard |
| Landing Page | `http://localhost:8080` | Project overview |
| Backend API | `http://localhost:8001` | REST API |
| API Docs | `http://localhost:8001/docs` | Auto-generated FastAPI docs |

### Running locally without Docker (optional)

Open three terminals:

```bash
# Terminal 1 — Backend
cd backend
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8001 app:app

# Terminal 2 — Frontend
cd frontend
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8000 app:app

# Terminal 3 — Landing
cd landing
uv sync
uv run uvicorn --app-dir src --host 0.0.0.0 --port 8080 main:app
```

### Expected inputs and outputs

**Text message:**
```
Input:  "I have experience with Python, SQL and Docker"
Output: "I found 12 skill gap(s). Missing skills: aws, ci/cd, java...
         Most in-demand: sql (6 jobs), java (5 jobs)..."
```

**PDF upload:**
1. Click the upload button (↑) in the chat
2. Select your resume PDF
3. Type a message like "Evaluate my resume"
4. Click Send — the PDF text is extracted client-side and sent with your message

**Quota exceeded:**
```
Output: "⚠️ Daily API quota exceeded. Please try again tomorrow
         or check your quota at https://ai.dev/rate-limit"
```

---

## API / Function Reference

### Backend Endpoints

#### `POST /chat`

Receives a user message and optional PDF text, runs skill gap analysis, and returns a response.

**Request payload:**
```json
{
    "message": "Help me find skill gaps in my resume",
    "pdf_text": "John Doe\nPython, SQL, Docker...\n"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | User's chat message |
| `pdf_text` | string or null | No | Extracted text from uploaded PDF |

**Response:**
```json
{
    "reply": "I found 8 skill gap(s).\n\nMissing skills: aws, java...\n\nMost in-demand: sql (6 jobs)"
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| `400` | Missing message and PDF text |
| `429` | Google API daily quota exceeded |
| `500` | Internal processing error |

---

#### `GET /health`

Health check endpoint.

```json
{"status": "ok"}
```

---

#### `GET /api/stats/tech-distribution`

Returns top 10 most required skills for the pie chart.

```json
{
    "labels": ["python", "sql", "docker", "java"],
    "values": [6, 5, 4, 3]
}
```

---

#### `GET /api/stats/jobs-per-source`

Returns tagged vs untagged job counts for the bar chart.

```json
{
    "labels": ["Tagged", "Untagged"],
    "values": [6, 2]
}
```

---

#### `GET /api/jobs/search?q=python`

Searches jobs by keyword in description or tech stack.

```json
{
    "results": [
        {
            "source_id": 91397216,
            "tech_stack": "Python, SQL, Docker",
            "description": "We are looking for a data engineer..."
        }
    ]
}
```

---

### Frontend Key Functions

| Function | File | Description |
|---|---|---|
| `sendMessage()` | `chat_pages.html` | Reads input, builds JSON payload, POSTs to `/chat`, renders reply |
| `appendUserMessage()` | `chat_pages.html` | Adds user bubble to chat history |
| `appendBotMessage()` | `chat_pages.html` | Adds bot bubble to chat history |
| `showTyping()` / `removeTyping()` | `chat_pages.html` | Shows animated typing indicator while waiting |
| `doSearch()` | `stats.html` | Fetches `/api/jobs/search` and renders results |
| `loadPieAndHBar()` | `stats.html` | Fetches `/api/stats/tech-distribution` and renders Charts.js charts |
| `loadBar()` | `stats.html` | Fetches `/api/stats/jobs-per-source` and renders bar chart |

### Frontend ↔ Backend Communication

```
Browser (localhost:8000)
    └── fetch POST http://backend:8001/chat   ← Docker internal network
            └── backend container processes request
                    └── returns JSON {"reply": "..."}
                            └── browser renders reply bubble
```

The `BACKEND_URL` environment variable is injected into the HTML via Jinja2 at render time:
```python
# app.py
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
templates.TemplateResponse(request=request, name="chat_pages.html",
                           context={"backend_url": BACKEND_URL})
```

```html
<!-- chat_pages.html -->
const BACKEND_URL = "{{ backend_url }}";
```

This means the URL is never hardcoded — switching between local and Docker only requires changing the `.env` file.

---

## Data / Assumptions

### JSON Message Format

Every chat request follows this structure:

```
User types message + optionally uploads PDF
        ↓
PDF.js extracts text client-side (browser, no server upload)
        ↓
fetch() sends: { message: "...", pdf_text: "..." or null }
        ↓
Backend writes resume_text to temp file
        ↓
_find_skill_gaps_async(tmp_path, DB_URL) called
        ↓
Gemini extracts skills → SQLite fetches job stacks → set subtraction
        ↓
SkillGapResult returned → formatted as string → {"reply": "..."}
        ↓
Frontend renders reply bubble
```

### Database Schema

The system reads from a SQLite database with this relevant structure:

| Column | Type | Description |
|---|---|---|
| `source_id` | INTEGER | Unique job identifier |
| `description` | TEXT | Raw job description |
| `tech_stack` | TEXT | Comma-separated skills (populated by Week 2 tag_data.py) |

### Assumptions

- Job descriptions are in English
- The `jobs_d1.db` database has already been tagged by `tag_data.py` before the backend starts
- PDF files are text-based (not scanned images) — image-only PDFs will extract empty text
- The Google API key has sufficient quota for the number of resumes being analysed
- `pdf_text` is extracted client-side using PDF.js — the PDF file itself is never sent to the server
- Skills listed as `"not specified"` or `"n/a"` in the database are filtered out before analysis
- Chat history is not persisted — refreshing the page clears all messages

---

## Testing

### Backend Tests

**Test health endpoint:**
```bash
curl http://localhost:8001/health
# Expected: {"status":"ok"}
```

**Test chat endpoint with curl:**
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Python, SQL, Docker developer", "pdf_text": null}'
# Expected: {"reply": "I found N skill gap(s)..."}
```

**Test with a PDF resume:**
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Evaluate my resume", "pdf_text": "John Doe\nSkills: Python, SQL, Git\nExperience: 2 years"}'
```

**Test stats endpoints:**
```bash
curl http://localhost:8001/api/stats/tech-distribution
curl http://localhost:8001/api/stats/jobs-per-source
curl "http://localhost:8001/api/jobs/search?q=python"
```

**Test quota error handling:**
Exhaust the API quota then send a message — the response should be HTTP 429 with a clear error message, not an indefinite wait.

### Frontend Tests

| Test Case | How to Reproduce | Expected Result |
|---|---|---|
| Send text message | Type in chat box, press Enter or Send | User bubble appears, typing indicator shows, bot replies |
| Upload PDF | Click ↑ button, select a PDF, send message | File name shown below input, PDF text sent with message |
| Clear PDF | Click ✕ next to file name | File removed, next message sent without PDF |
| Backend unreachable | Stop backend, send message | "⚠️ Could not reach the backend. Is it running?" |
| Quota exceeded | Exhaust API key, send message | "⚠️ Daily API quota exceeded..." shown immediately |
| Stats page charts | Visit `http://localhost:8000/stats` | Pie chart, bar charts, and search bar all render |
| Job search | Type "python" in search bar, press Enter | Job results shown with skill badges |

### Docker Communication Test

```bash
# Verify both containers are on the same network
docker network inspect week_3_app-network

# Verify frontend can reach backend internally
docker exec -it week_3-frontend-1 curl http://backend:8001/health
# Expected: {"status":"ok"}
```

---

## Limitations

- **No chat history persistence** — messages are lost on page refresh. A database like Redis or PostgreSQL would be needed to store conversations.
- **No user authentication** — anyone with access to the URL can use the chatbot. There is no login or session management.
- **API quota limits** — the free tier of the Google Gemini API allows only 20 requests per day per model. Heavy usage will hit this limit quickly.
- **PDF extraction quality** — PDF.js only extracts text from digital PDFs. Scanned PDFs (image-based) will return empty text and produce no skill gap results.
- **Small job database** — with only 8 tagged jobs, demand statistics have limited statistical significance. The percentages and demand levels are relative to this small sample.
- **Skill matching is exact** — the set subtraction uses exact lowercase string matching. Near-matches like `"postgres"` vs `"postgresql"` are treated as different skills, causing false positives in the gap list.
- **C/C++ splitting** — despite prompt instructions, Gemini occasionally splits `C/C++` into `C` and `C++` as separate skills, causing inaccurate gap detection for candidates with this skill.
- **No streaming response** — the entire analysis must complete before any reply is shown. For large databases with many normalisation batches, this can take over a minute.
- **Single language support** — resumes and job descriptions in languages other than English are not supported.
- **MCP removed from backend** — the MCP (Model Context Protocol) server is used in Week 2 standalone scripts but was replaced with direct SQLite access in the backend due to Windows subprocess environment variable propagation issues.

---

## Architecture Reflection

### Design Choices

The project follows a **microservices architecture** with three independently deployable services. This was chosen deliberately over a monolithic approach for several reasons.

Separating frontend and backend means the chat interface and the AI processing logic can be developed, tested, and scaled independently. The frontend only knows about the `/chat` endpoint — it doesn't care how the backend works internally. This separation also makes it straightforward to swap the backend AI model or switch from Gemini to a local LLM without touching any frontend code.

Docker was chosen as the containerisation tool because it eliminates the "works on my machine" problem. Every developer and every deployment environment gets an identical runtime, from Python version to installed packages. The `docker compose` setup means spinning up the entire stack is a single command regardless of the host operating system.

The **bridge network** (`app-network`) was used instead of the host network driver as required, which means inter-service communication uses service names (`http://backend:8001`) rather than `localhost`. This is more secure and more representative of a real cloud deployment where services are isolated.

### Trade-offs

**Simplicity over scalability** — using SQLite directly instead of a proper database server like PostgreSQL keeps the setup simple and dependency-free. For a production system with concurrent users, SQLite's single-writer limitation would become a bottleneck.

**Client-side PDF extraction** — extracting PDF text in the browser using PDF.js means the PDF file is never uploaded to the server. This is a privacy-friendly approach but limits handling of complex PDFs (scanned, encrypted, or image-heavy).

**Direct SQLite over MCP** — the original Week 2 design used MCP to decouple database access. This was simplified to direct `sqlite3` calls in the backend after repeated subprocess issues on Windows. The trade-off is less architectural purity for significantly more reliability.

**Bootstrap over a frontend framework** — Bootstrap with vanilla JavaScript was chosen over React or Vue for simplicity and to match the requirement. A component-based framework would make the chat history easier to manage as state but adds build tooling complexity.

### Improvements

Given more time, these would be the priority improvements:

- **Persistent chat history** — store conversations in a database so users can return to previous sessions. A simple approach would be SQLite with a `conversations` table; a more scalable approach would use Redis.
- **Streaming responses** — use FastAPI's `StreamingResponse` and server-sent events so the bot reply appears word by word rather than all at once after a long wait.
- **Better skill matching** — build a canonical skill dictionary (e.g. `postgres → postgresql`, `k8s → kubernetes`) to reduce false positives from near-match skill names.
- **Cloud deployment** — deploy each service to Railway or Render with environment variables managed through the platform dashboard, making the application publicly accessible without running Docker locally.
- **React frontend** — replace the Jinja2 template with a React app for better state management, component reuse, and a more responsive user experience.