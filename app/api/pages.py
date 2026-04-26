"""Web page routes (Jinja2 rendered pages)."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active": "dashboard"})


@router.get("/accounts")
async def accounts_page(request: Request):
    return templates.TemplateResponse("accounts.html", {"request": request, "active": "accounts"})


@router.get("/workers")
async def workers_page(request: Request):
    return templates.TemplateResponse("workers.html", {"request": request, "active": "workers"})


@router.get("/posts")
async def posts_page(request: Request):
    return templates.TemplateResponse("posts.html", {"request": request, "active": "posts"})


@router.get("/logs")
async def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request, "active": "logs"})
