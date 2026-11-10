"""Dash application entry point, mounted behind FastAPI administrative access."""
from pathlib import Path

import dash

from lab_hub.config import get_settings
from .callbacks import register_callbacks
from .layout import build_layout

settings = get_settings()
app = dash.Dash(__name__, requests_pathname_prefix="/dashboard/", routes_pathname_prefix="/",
    assets_folder=str(Path(__file__).resolve().parent / "assets"), external_stylesheets=["/static/theme.css"],
    title="Re-Fab · Residuos del laboratorio", suppress_callback_exceptions=True)
app.index_string = app.index_string.replace("<html>", '<html lang="es">').replace(
    "{%favicon%}", '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">')
server = app.server
app.layout = build_layout(settings.DASHBOARD_NEW_RECORD_URL)
register_callbacks(app, settings.DASHBOARD_NEW_RECORD_URL)
