from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/")
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")