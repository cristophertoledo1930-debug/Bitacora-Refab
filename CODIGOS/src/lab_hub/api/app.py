from fastapi import FastAPI, Depends, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import OperationalError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from lab_hub.config import get_settings
from lab_hub.db.session import get_db
from lab_hub.api.routes import router

settings = get_settings()

app = FastAPI(
    title="QR Lab Hub API",
    description="API de registro de residuos de laboratorio y reportería",
    version="0.1.0"
)


@app.middleware("http")
async def administrative_access(request: Request, call_next):
    # Desktop mode is explicitly enabled only for this loopback deployment.
    local = (
        settings.LOCAL_DESKTOP_ACCESS
        and settings.APP_ENV == "development"
        and request.client is not None
        and request.client.host in {"127.0.0.1", "::1"}
        and request.url.hostname in {"localhost", "127.0.0.1", "::1"}
        and request.headers.get("sec-fetch-site", "none") != "cross-site"
    )
    request.state.local_admin = local
    if request.url.path.startswith("/dashboard"):
        authorized = local or settings.ADMIN_API_KEY in (
            request.headers.get("X-Admin-Key"), request.cookies.get("admin_session")
        )
        if not authorized:
            return JSONResponse(status_code=401, content={"detail": "Acceso administrativo requerido."})
    return await call_next(request)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/dashboard/")


@app.exception_handler(OperationalError)
async def database_unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible. Reintente con la misma clave."})


@app.get("/health/live", summary="Liveness probe")
def health_live():
    """Confirms the FastAPI application process is alive."""
    return {"status": "ok", "service": "qr-lab-hub"}


@app.get("/health/ready", summary="Readiness probe")
def health_ready(db: Session = Depends(get_db)):
    """Verifies PostgreSQL connectivity and availability."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": "disconnected"}
        )


from starlette.middleware.wsgi import WSGIMiddleware
from lab_hub.dashboard.app import app as dash_app

app.include_router(router)
app.mount("/dashboard", WSGIMiddleware(dash_app.server))
