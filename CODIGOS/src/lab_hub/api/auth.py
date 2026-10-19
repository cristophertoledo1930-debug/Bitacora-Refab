from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import APIKeyHeader, APIKeyCookie
from lab_hub.config import get_settings

settings = get_settings()

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
api_key_cookie = APIKeyCookie(name="admin_session", auto_error=False)


def require_admin(
    request: Request,
    key_from_header: str | None = Security(api_key_header),
    key_from_cookie: str | None = Security(api_key_cookie)
) -> bool:
    """
    Validates administrative access either via X-Admin-Key header or admin_session cookie.
    Used for dashboard, admin stats, reports download, and full record listing.
    """
    # Accept header or cookie matching configured ADMIN_API_KEY
    if getattr(request.state, "local_admin", False):
        return True
    if key_from_header and key_from_header == settings.ADMIN_API_KEY:
        return True
    if key_from_cookie and key_from_cookie == settings.ADMIN_API_KEY:
        return True

    # If neither matched, raise 401 Unauthorized
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acceso administrativo no autorizado. Requiere clave de administrador."
    )

