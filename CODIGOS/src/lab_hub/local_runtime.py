"""Local supervisor: SMTP inbox, daily reports and HTTP server on loopback."""
from pathlib import Path
import logging
import subprocess
import sys
import threading
import uuid
import argparse
import json
from datetime import datetime, timezone

from aiosmtpd.controller import Controller
from lab_hub.config import get_settings
from lab_hub.db.session import SessionLocal
from lab_hub.jobs.monthly_report import run_daily_check


class LocalInbox:
    async def handle_DATA(self, server, session, envelope):
        inbox = Path("storage/mail")
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / f"{uuid.uuid4()}.eml").write_bytes(envelope.original_content)
        return "250 Stored locally"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8071)
    args = parser.parse_args()
    settings = get_settings()
    from lab_hub.services.relocate_reports import relocate_reports
    with SessionLocal() as db:
        relocate_reports(db)
    stop = threading.Event()
    stop_file = Path("storage/local.stop")
    stop_file.unlink(missing_ok=True)
    smtp = Controller(LocalInbox(), hostname="127.0.0.1", port=settings.SMTP_PORT)
    smtp.start()

    def reports():
        while not stop.is_set():
            try:
                with SessionLocal() as db:
                    run_daily_check(db)
            except Exception:
                logging.error("Informe pendiente; se reintentará en cinco minutos.")
            stop.wait(300)

    worker = threading.Thread(target=reports, daemon=True)
    worker.start()
    def weekly_reports():
        from lab_hub.jobs.weekly_report import refresh_weekly_reports
        from lab_hub.jobs.monthly_report import refresh_monthly_reports
        while not stop.is_set():
            try:
                with SessionLocal() as db:
                    refresh_weekly_reports(db)
                with SessionLocal() as db:
                    refresh_monthly_reports(db)
            except Exception:
                logging.error("Informes automáticos pendientes; se reintentará en 15 segundos.")
            stop.wait(15)

    weekly_worker = threading.Thread(target=weekly_reports, daemon=True)
    weekly_worker.start()
    def sheets():
        from lab_hub.services.sheets import sync_once
        while not stop.is_set():
            status = {"checked_at": datetime.now(timezone.utc).isoformat()}
            try:
                result = sync_once()
                status.update(result)
                logging.warning("Sheets: creados=%s existentes=%s rechazados=%s",
                                result["created"], result["existing"], result["rejected"])
            except Exception:
                status["error"] = True
                logging.error("Sheets: sincronización pendiente; se reintentará en 60 segundos.")
            target = Path("storage/sheets-status.json")
            try:
                temporary = target.with_suffix(".tmp")
                temporary.write_text(json.dumps(status), encoding="utf-8")
                temporary.replace(target)
            except OSError:
                logging.error("Sheets: no se pudo guardar el estado local.")
            stop.wait(60)

    sheets_worker = None
    if settings.GOOGLE_SHEETS_ID:
        sheets_worker = threading.Thread(target=sheets, daemon=True)
        sheets_worker.start()
    server = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "lab_hub.api.app:app",
        "--host", "127.0.0.1", "--port", str(args.port), "--no-access-log", "--no-proxy-headers",
    ])
    try:
        while server.poll() is None and not stop_file.exists():
            stop.wait(1)
    finally:
        stop.set()
        worker.join(timeout=30)
        weekly_worker.join(timeout=30)
        if sheets_worker:
            sheets_worker.join(timeout=25)
        server.terminate()
        server.wait(timeout=15)
        smtp.stop()
        stop_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
