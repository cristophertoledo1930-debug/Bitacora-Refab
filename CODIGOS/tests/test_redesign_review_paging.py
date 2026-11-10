from lab_hub.dashboard.callbacks import render_records, table_page
from lab_hub.dashboard.data import load_snapshot, parse_filters
from lab_hub.db.session import SessionLocal
from tests.test_f3_dashboard import clean_control_fixture  # noqa: F401
from tests.test_redesign_ui import live_fixture  # noqa: F401


def test_page_resets_only_for_filters_or_order_and_clamps_on_tick():
    snapshot = {"filters": parse_filters("month"), "agg": {"total_records": 60}}
    _, context = table_page(snapshot, 0, [])
    assert table_page(snapshot, 2, [], context)[0] == 2
    assert table_page(snapshot, 2, [{"column_id": "weight", "direction": "asc"}], context)[0] == 0
    for changes in ({"source": "esp32"}, {"preset": "custom"}, {"start_date": "2026-01-01"}, {"end_date": "2026-02-01"}):
        filtered = {**snapshot, "filters": {**snapshot["filters"], **changes}}
        assert table_page(filtered, 2, [], context)[0] == 0
    reduced = {**snapshot, "agg": {"total_records": 26}}
    assert table_page(reduced, 2, [], context)[0] == 1
    empty = {**snapshot, "agg": {"total_records": 0}}
    assert table_page(empty, 2, [], context)[0] == 0


def test_page_three_to_one_page_queries_first_page(clean_control_fixture):  # noqa: F811
    filters = parse_filters("all")
    with SessionLocal() as db:
        snapshot = load_snapshot(db, filters)
    _, context = table_page(snapshot, 0, [])
    result = render_records(snapshot, 2, [], context)
    assert len(result[0]) == 3
    assert result[4] == "1 / 1"
    assert result[6] == 0


def test_browser_page_three_filter_to_one_page(live_fixture):  # noqa: F811
    from datetime import datetime
    from pathlib import Path
    from urllib.parse import urlsplit

    from fastapi.testclient import TestClient
    from playwright.sync_api import sync_playwright

    from lab_hub.api.app import app
    from lab_hub.config import get_settings
    from lab_hub.db.models import WasteRecord

    settings = get_settings()
    with SessionLocal() as db:
        db.add(WasteRecord(**live_fixture, recorded_at=datetime.now(settings.timezone), weight_g=100,
            source="esp32", idempotency_key="review-paging-unique", payload_hash="synthetic"))
        db.commit()
    client = TestClient(app, base_url="http://review.test")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 1000},
                               extra_http_headers={"X-Admin-Key": settings.ADMIN_API_KEY})
        def proxy(route):
            req = route.request
            url = urlsplit(req.url)
            response = client.request(req.method, url.path + ("?" + url.query if url.query else ""),
                                      content=req.post_data_buffer, headers=req.headers)
            headers = {key: value for key, value in response.headers.items() if key not in {"content-length", "content-encoding"}}
            route.fulfill(status=response.status_code, headers=headers, body=response.content)
        page.route("http://review.test/**", proxy)
        page.goto("http://review.test/dashboard/", wait_until="networkidle")
        page.wait_for_selector(".kpi-grid")
        for label in ("2 / 3", "3 / 3"):
            page.get_by_role("button", name="Siguiente", exact=True).click()
            page.wait_for_function("text => document.querySelector('#page-label').textContent === text", arg=label)
        page.locator("#filters-summary").click()
        page.locator("#filter-source").click()
        page.get_by_role("option", name="ESP32", exact=True).click()
        page.wait_for_function("document.querySelector('#page-label').textContent === '1 / 1'")
        assert page.locator(".record-card").count() == 1
        assert "ESP32" in page.locator(".record-card").inner_text()
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(Path("docs/redesign/codex/evidencias/review-r02-paging.png")), full_page=True)
        browser.close()
