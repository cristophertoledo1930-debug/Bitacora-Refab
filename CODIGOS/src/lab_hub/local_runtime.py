"""Local supervisor: SMTP inbox, daily reports and HTTP server on loopback."""
from pathlib import Path
from datetime import datetime
import logging
import subprocess
import sys
import threading
import uuid
import argparse

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
        server.terminate()
        server.wait(timeout=15)
        smtp.stop()
        stop_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
