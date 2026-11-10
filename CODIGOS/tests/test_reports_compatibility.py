"""Templates remain usable while an older local worker is still running."""
from starlette.requests import Request
from lab_hub.api.routes import templates


def test_reports_template_accepts_previous_worker_context():
    request = Request({"type": "http", "method": "GET", "path": "/reports",
                       "headers": [], "scheme": "http", "server": ("localhost", 8071),
                       "query_string": b""})
    response = templates.TemplateResponse(request=request, name="reports.html", context={
        "reports": [], "current_period": "2026-11",
    })
    assert response.status_code == 200
    assert "Estado del correo temporalmente no disponible" in response.body.decode()
    assert "Generar o recuperar PDF" in response.body.decode()
