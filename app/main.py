import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import require_auth, auth_enabled
from app.config import settings
from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler
from app.api.incidents import router as incidents_router
from app.api.test import router as test_router
from app.api.settings import router as settings_router
from app.api.devices import router as devices_router
from app.services import notification_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("alertbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    logger.info("%s ready — auth %s", settings.APP_NAME, "ON" if auth_enabled() else "OFF")
    yield
    stop_scheduler()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(incidents_router)
app.include_router(test_router)
app.include_router(settings_router)
app.include_router(devices_router)


def _page(request: Request, name: str, active: str, title: str):
    return templates.TemplateResponse(
        request,
        name,
        {
            "app_name": settings.APP_NAME,
            "active": active,
            "page_title": title,
            "auth_enabled": auth_enabled(),
        },
    )


@app.get("/")
def dashboard(request: Request, _=Depends(require_auth)):
    return _page(request, "dashboard.html", "dashboard", "Live incidents")


@app.get("/history")
def history(request: Request, _=Depends(require_auth)):
    return _page(request, "history.html", "history", "Incident history")


@app.get("/incident/{incident_id}")
def incident_detail(request: Request, incident_id: int, _=Depends(require_auth)):
    return templates.TemplateResponse(
        request,
        "incident.html",
        {
            "app_name": settings.APP_NAME,
            "active": "history",
            "page_title": f"Incident #{incident_id}",
            "incident_id": incident_id,
            "auth_enabled": auth_enabled(),
        },
    )


@app.get("/settings")
def settings_page(request: Request, _=Depends(require_auth)):
    return _page(request, "settings.html", "settings", "Settings")


@app.get("/setup")
def setup_page(request: Request, _=Depends(require_auth)):
    return _page(request, "setup.html", "setup", "Phone setup")


@app.get("/healthz")
def healthz():
    """Uptime probe for Render — deliberately unauthenticated."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/health")
def api_health(_=Depends(require_auth)):
    from app.scheduler import job_status

    return {
        "status": "ok",
        "mailbox_configured": bool(settings.GMAIL_EMAIL and settings.GMAIL_APP_PASSWORD),
        "channels": notification_service.channel_status(),
        "jobs": job_status(),
    }


# --- PWA plumbing --------------------------------------------------------
# The service worker must be served from the site root to control every page.
@app.get("/sw.js")
def service_worker():
    return FileResponse("app/static/sw.js", media_type="application/javascript")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse("app/static/manifest.webmanifest", media_type="application/manifest+json")


@app.get("/offline")
def offline(request: Request):
    return templates.TemplateResponse(
        request,
        "offline.html",
        {"app_name": settings.APP_NAME, "page_title": "Offline", "active": "", "auth_enabled": False},
    )


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return templates.TemplateResponse(
        request,
        "offline.html",
        {
            "app_name": settings.APP_NAME,
            "page_title": "Not found",
            "active": "",
            "auth_enabled": False,
        },
        status_code=404,
    )
