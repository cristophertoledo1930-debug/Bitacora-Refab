"""Synthetic PostgreSQL + real Chromium acceptance for the dashboard redesign."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from urllib.parse import urlsplit

import dash
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
import pytest

from lab_hub.api.app import app
from lab_hub.config import get_settings
from lab_hub.dashboard import callbacks
from lab_hub.dashboard.components import monthly_chart, ranking_chart, ranking_rows
from lab_hub.db.models import WasteRecord
from lab_hub.db.session import SessionLocal
from tests.test_f3_dashboard import clean_control_fixture  # noqa: F401

OUTPUT = Path("docs/redesign/codex/evidencias")


def test_invalid_dates_and_database_failure_are_atomic(monkeypatch):
    def unavailable():
        raise RuntimeError("must never reach browser")
    monkeypatch.setattr(callbacks, "SessionLocal", unavailable)
    args = ("ALL",) * 5
    invalid = callbacks.refresh_data(0, "custom", "2026-11-09", "2026-11-01", *args, None)
    assert invalid[0] is dash.no_update
    assert "inicial" in invalid[2]
    assert invalid[3] is dash.no_update
    previous = {"updated": "12:30:00", "agg": {"total_records": 3}}
    failed = callbacks.refresh_data(0, "all", None, None, *args, previous)
    assert failed[0] is dash.no_update
    assert "12:30:00" in failed[1]
    assert "stale" in failed[3]
    assert "must never" not in failed[1]


def test_rankings_top_eight_others_and_current_month():
    rows = [{"name": f"Causa {i}", "count": i, "total_weight_g": str(i * 100)} for i in range(14)]
    ranked = ranking_rows(rows, "kg")
    assert len(ranked) == 9
    assert ranked[-1]["name"] == "Otros (5)"
    assert sum(Decimal(r["total_weight_g"]) for r in ranked) == 9100
    figure = ranking_chart(rows, "Por causa")
    assert figure.data[0].marker.color == "#64D6A0"
    assert "1,30 kg" in figure.data[0].text[0]
    now = datetime.now(get_settings().timezone)
    figure = monthly_chart([{"period": now.strftime("%Y-%m"), "label": "mes actual", "count": 1, "total_weight_g": "5"}])
    assert figure.data[0].marker.opacity == (0.45,)
    assert "en curso" in figure.data[0].x[0]


@pytest.fixture
def live_fixture(clean_control_fixture):  # noqa: F811
    with SessionLocal() as db:
        seed = db.query(WasteRecord).first()
        now = datetime.now(get_settings().timezone)
        seed_values = {field: getattr(seed, field) for field in ("waste_type_id", "material_id", "machine_id", "cause_id")}
        for i in range(55):
            db.add(WasteRecord(**seed_values, recorded_at=now, weight_g=Decimal("100"),
                source="google_forms" if i % 2 else "manual", idempotency_key=f"ui-{i}", payload_hash="synthetic"))
        db.commit()
    return seed_values


def test_responsive_keyboard_paging_csv_and_errors(live_fixture, monkeypatch):
    OUTPUT.mkdir(exist_ok=True)
    settings = get_settings()
    client = TestClient(app, base_url="http://redesign.test")
    checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(extra_http_headers={"X-Admin-Key": settings.ADMIN_API_KEY}, reduced_motion="reduce")
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        def proxy(route):
            req = route.request
            url = urlsplit(req.url)
            response = client.request(req.method, url.path + ("?" + url.query if url.query else ""),
                                      content=req.post_data_buffer, headers=req.headers)
            if url.path.endswith("_dash-update-component"):
                payload = json.loads(req.post_data)
                requests.append({"output": payload["output"], "inputs": payload.get("inputs"),
                                 "response": response.text[:500]})
            headers = {k: v for k, v in response.headers.items() if k not in {"content-encoding", "content-length"}}
            route.fulfill(status=response.status_code, headers=headers, body=response.content)
        page.route("http://redesign.test/**", proxy)
        for width in (320, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto("http://redesign.test/dashboard/", wait_until="networkidle")
            try:
                page.wait_for_selector(".kpi-grid", timeout=10000)
            except Exception:
                (OUTPUT / "browser-debug.txt").write_text(page.locator("body").inner_text() + "\n" + str(errors), encoding="utf-8")
                page.screenshot(path=str(OUTPUT / "browser-debug.png"), full_page=True)
                raise
            assert page.locator(".kpi").count() == 4
            assert page.locator(".kpi-value").first.inner_text() == "5,50 kg"
            assert page.locator("#preset-month").get_attribute("aria-pressed") == "true"
            assert page.locator("html").get_attribute("lang") == "es"
            labels = page.locator("label[for]").evaluate_all("els => els.filter(e => !e.control).map(e => e.htmlFor)")
            assert not labels, page.locator(".filter").first.inner_html()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.wait_for_selector("#chart-by-source .barlayer .point path")
            heights = page.locator("#chart-by-source .barlayer .point path").evaluate_all("els => els.map(e => e.getBBox().height)")
            assert all(16 <= height <= 20 for height in heights), heights
            if width in (390, 1440):
                page.locator("#chart-by-source").locator("xpath=../..").screenshot(path=str(OUTPUT / f"origin-{width}.png"))
                bar = page.locator("#chart-by-source .barlayer .point path").first.bounding_box()
                page.mouse.move(bar["x"] + bar["width"] / 2, bar["y"] + bar["height"] / 2)
                page.wait_for_selector("#chart-by-source .hoverlayer .hovertext")
                assert "Manual" in page.locator("#chart-by-source .hoverlayer").text_content()
                page.mouse.move(0, 0)
                page.evaluate("window.scrollTo(0, 0)")
            if width < 768:
                assert not page.locator("#filters-panel").evaluate("e => e.open")
                assert page.locator(".record-card").count() == 25
            page.screenshot(path=str(OUTPUT / f"dashboard-{width}.png"), full_page=True)
            if width in (390, 1440):
                page.screenshot(path=str(OUTPUT / f"dashboard-{width}-viewport.png"))
            # Every visible actionable element must have at least 44px target height.
            small = page.locator("button, summary, .button, .filter .Select-control").evaluate_all(
                "els => els.filter(e => e.getClientRects().length && e.getBoundingClientRect().height < 43.9).map(e => ({text:e.textContent,height:e.getBoundingClientRect().height}))")
            assert not small, small
            checks.append({"width": width, "overflow": False, "kpis": 4, "rows": 25})
        page.get_by_role("button", name="Este mes", exact=True).focus()
        assert page.locator("#preset-month").evaluate("e => getComputedStyle(e).outlineStyle") == "solid"
        page.locator("#filter-waste_type_id").click()
        page.wait_for_selector('[role="listbox"]')
        page.screenshot(path=str(OUTPUT / "filters-open.png"), full_page=True)
        styles = page.locator('input[placeholder]').evaluate_all("els => els.map(e => ({placeholder:e.placeholder,color:getComputedStyle(e,'::placeholder').color,background:getComputedStyle(e).backgroundColor,html:e.outerHTML}))")
        (OUTPUT / "input-styles.json").write_text(json.dumps(styles, ensure_ascii=False, indent=2), encoding="utf-8")
        assert all(item["color"] == "rgb(188, 206, 195)" for item in styles), styles
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Personalizado", exact=True).click()
        page.locator("#filter-start").fill("2026-11-09")
        page.locator("#filter-end").fill("2026-11-01")
        page.locator("#filter-end").press("Tab")
        try:
            page.wait_for_function("document.querySelector('#date-error').textContent.includes('inicial')", timeout=5000)
        except Exception:
            (OUTPUT / "date-debug.json").write_text(json.dumps(requests[-20:], ensure_ascii=False, indent=2), encoding="utf-8")
            page.screenshot(path=str(OUTPUT / "date-debug.png"), full_page=True)
            raise
        assert page.locator(".kpi-value").first.inner_text() == "5,50 kg"
        assert page.locator("#filter-start").get_attribute("aria-describedby") == "date-error"
        page.screenshot(path=str(OUTPUT / "invalid-dates.png"), full_page=True)
        page.get_by_role("button", name="Este mes", exact=True).click()
        page.wait_for_function("!document.querySelector('#date-error').textContent")
        try:
            page.wait_for_function("document.querySelector('#chart-monthly')?.getBoundingClientRect().height >= 300", timeout=5000)
        except Exception:
            (OUTPUT / "height-debug.txt").write_text(page.locator('#chart-monthly').evaluate("e => e.outerHTML.slice(0,800) + ' computed:' + getComputedStyle(e).height + ' display:' + getComputedStyle(e).display"), encoding="utf-8")
            raise
        # The mobile pager uses the same server-side page_current as DataTable.
        page.set_viewport_size({"width": 390, "height": 1000})
        page.get_by_role("button", name="Siguiente", exact=True).click()
        page.wait_for_function("document.querySelector('#page-label').textContent.startsWith('2 /')")
        with SessionLocal() as db:
            db.add(WasteRecord(**live_fixture, recorded_at=datetime.now(settings.timezone), weight_g=500,
                source="manual", idempotency_key="ui-live-new", payload_hash="synthetic"))
            db.commit()
        page.wait_for_timeout(15500)
        assert page.locator("#page-label").inner_text() == "2 / 3"
        assert page.locator(".kpi-value").first.inner_text() == "6,00 kg"
        assert page.locator(".kpi-value").nth(1).inner_text() == "56"
        with page.expect_download() as pending:
            page.get_by_role("button", name="Exportar CSV", exact=True).click()
        download = pending.value
        csv_path = OUTPUT / "filtered.csv"
        download.save_as(csv_path)
        assert len(csv_path.read_text(encoding="utf-8-sig").splitlines()) == 57
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)
        # Database failure retains prior values and exposes the previous update time.
        def unavailable():
            raise RuntimeError("synthetic unavailable")
        with monkeypatch.context() as patch:
            patch.setattr(callbacks, "SessionLocal", unavailable)
            page.get_by_role("button", name="Todo", exact=True).click()
            page.wait_for_selector("#dashboard-content.stale")
            assert "desactualizados desde" in page.locator("#error-banner").inner_text()
            assert page.locator("#error-banner").get_attribute("role") == "alert"
            assert page.locator(".kpi-value").first.inner_text() == "6,00 kg"
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUTPUT / "database-error.png"), full_page=True)
        page.get_by_role("button", name="Mes anterior", exact=True).click()
        page.wait_for_selector(".empty-state")
        assert page.locator(".kpi").count() == 0
        assert page.locator(".empty-state").count() == 1
        page.screenshot(path=str(OUTPUT / "empty.png"), full_page=True)
        page.get_by_role("button", name="Limpiar filtros", exact=True).click()
        page.wait_for_selector(".kpi-grid")
        assert not errors, errors
        browser.close()
    (OUTPUT / "responsive.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
