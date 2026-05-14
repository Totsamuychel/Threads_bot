"""Web page routes (Jinja2 rendered pages)."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"active": "dashboard"})


@router.get("/accounts")
async def accounts_page(request: Request):
    return templates.TemplateResponse(request=request, name="accounts.html", context={"active": "accounts"})


@router.get("/workers")
async def workers_page(request: Request):
    return templates.TemplateResponse(request=request, name="workers.html", context={"active": "workers"})


@router.get("/posts")
async def posts_page(request: Request):
    return templates.TemplateResponse(request=request, name="posts.html", context={"active": "posts"})


@router.get("/logs")
async def logs_page(request: Request):
    return templates.TemplateResponse(request=request, name="logs.html", context={"active": "logs"})
