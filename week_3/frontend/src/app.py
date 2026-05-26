import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")


@app.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse(request=request, name="chat_pages.html", context={"backend_url": BACKEND_URL}, )