"""Capture synthetic UI evidence in a new PostgreSQL database; clean up afterwards."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

import httpx
import psycopg
from psycopg import sql
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["before", "after"])
    parser.add_argument("--postgres-dsn", default="postgresql://postgres@127.0.0.1:55432/postgres")
    args = parser.parse_args()
    name = "qrlabhub_ui_" + uuid.uuid4().hex[:12]
    output = Path("docs/evidencias/google_forms_ui")
    output.mkdir(parents=True, exist_ok=True)
    process = None
    with psycopg.connect(args.postgres_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        from sqlalchemy.engine import make_url
        database_url = make_url(args.postgres_dsn).set(drivername="postgresql+psycopg", database=name).render_as_string(hide_password=False)
        os.environ.update(DATABASE_URL=database_url, ADMIN_API_KEY="synthetic-ui-verification",
            LOCAL_DESKTOP_ACCESS="false", EMAIL_ENABLED="false", LOCAL_SMTP_ENABLED="false",
            REPORT_OUTPUT_DIR=str(Path(".tools/ui-reports") / name))
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config("alembic.ini"), "head")
        from lab_hub.db.session import SessionLocal, engine
        from lab_hub.services.seeds import seed_catalogs
        from lab_hub.services.records import create_waste_record
        from lab_hub.jobs.monthly_report import process_monthly_report
        from lab_hub.config import get_settings
        from datetime import datetime
        with SessionLocal() as db:
            cats = seed_catalogs(db)
            for source, weight in [("manual", "125"), ("google_forms", "375"), ("manual", "1000")]:
                create_waste_record(db, idempotency_key=uuid.uuid4().hex, qr_token="token-laser-01",
                    waste_type_id=cats["waste_types"]["laser_cut"].id, material_id=cats["materials"]["acrylic"].id,
                    machine_id=cats["machines"]["laser_cutter_1"].id, cause_id=cats["causes"]["cut_margin"].id,
                    weight_str=weight, source=source)
            process_monthly_report(db, datetime.now(get_settings().timezone).strftime("%Y-%m"))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        with (output / (args.phase + "-server.log")).open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-m", "uvicorn", "lab_hub.api.app:app",
                "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(80):
                try:
                    if httpx.get(base + "/health/ready").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("UI server not ready; see evidence server log")
            results = []
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(extra_http_headers={"X-Admin-Key": "synthetic-ui-verification"},
                    viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                for width, height, device in [(1440, 1050, "desktop"), (390, 844, "mobile")]:
                    page.set_viewport_size({"width": width, "height": height})
                    for route, label in [("/r/token-laser-01", "form"), ("/reports", "reports"),
                                         ("/r/invalid-synthetic", "error"), ("/dashboard/", "dashboard")]:
                        page.goto(base + route, wait_until="networkidle")
                        if label == "dashboard":
                            page.wait_for_function("document.querySelectorAll('.kpi-value')[1]?.textContent === '3'")
                            page.wait_for_selector("#chart-by-type .main-svg")
                        page.screenshot(path=str(output / f"{args.phase}-{label}-{device}.png"), full_page=True)
                        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                        results.append({"page": label, "device": device, "horizontal_overflow": overflow})
                        if args.phase == "after":
                            assert not overflow, f"Overflow {label} {device}"
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(base + "/r/token-laser-01", wait_until="networkidle")
                page.locator('#weight').fill('-1')
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state('networkidle')
                assert page.locator('#weight').input_value() == '-1'
                page.screenshot(path=str(output / f"{args.phase}-form-validation-mobile.png"), full_page=True)
                page.locator('#weight').fill('125')
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state('networkidle')
                assert '125.000' in page.locator('body').inner_text()
                page.screenshot(path=str(output / f"{args.phase}-success-mobile.png"), full_page=True)
                if args.phase == "after":
                    page.goto(base + '/dashboard/', wait_until='networkidle')
                    page.wait_for_function("document.querySelector('#card-total-records')?.textContent === '4'")
                    page.locator('#navigation-panel > summary').click()
                    page.locator('#filter-source').click()
                    page.locator('#navigation-panel').get_by_text('Google Forms', exact=True).click()
                    page.wait_for_function("document.querySelector('#card-total-records')?.textContent === '1'")
                    assert 'Google Forms' in page.locator('#forms-reception').inner_text()
                    page.screenshot(path=str(output / 'after-dashboard-filtered-mobile.png'), full_page=True)
                    # Keyboard reaches controls with visible focus; weight uses decimal input.
                    page.goto(base + '/r/token-laser-01', wait_until='networkidle')
                    page.keyboard.press('Tab')
                    focus = page.evaluate("({tag:document.activeElement.tagName, outline:getComputedStyle(document.activeElement).outlineStyle})")
                    assert focus['tag'] in ['A', 'SELECT', 'INPUT', 'BUTTON']
                    assert focus['outline'] != 'none'
                    assert page.locator('#weight').get_attribute('inputmode') == 'decimal'
                    for selector in ['#weight', '#unit', '#waste_type_id', '.submit-btn']:
                        assert page.locator(selector).bounding_box()['height'] >= 44
                assert not errors, errors
                browser.close()
            import json
            (output / f"{args.phase}-checks.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
            count = len(list(output.glob(args.phase + "-*.png")))
            print(f"{args.phase}: {count} screenshots; browser errors: {len(errors)}")
    finally:
        if process:
            process.terminate()
            process.wait(timeout=15)
        if 'engine' in locals():
            engine.dispose()
        with psycopg.connect(args.postgres_dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    main()
