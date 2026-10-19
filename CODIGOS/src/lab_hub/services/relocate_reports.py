"""Recover report paths after moving the project, without altering PDF contents."""
from hashlib import sha256
from pathlib import Path, PureWindowsPath
from lab_hub.config import get_settings
from lab_hub.db.models import ReportRun


def relocate_reports(db):
    root = Path(get_settings().REPORT_OUTPUT_DIR).resolve()
    changed = 0
    for run in db.query(ReportRun).all():
        if not run.pdf_path or Path(run.pdf_path).exists():
            continue
        candidate = root / PureWindowsPath(run.pdf_path).name
        if candidate.is_file() and sha256(candidate.read_bytes()).hexdigest() == run.content_hash:
            run.pdf_path = str(candidate)
            changed += 1
    db.commit()
    return changed
