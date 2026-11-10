from pathlib import Path

from lab_hub.dashboard.components import monthly_chart, origin, ranking_chart, tokens


def test_render_multiple_figures_reads_css_only_once(monkeypatch):
    reads = []
    real_read = Path.read_text
    def tracked_read(path, *args, **kwargs):
        if path.suffix == ".css":
            reads.append(path.name)
        return real_read(path, *args, **kwargs)
    tokens.cache_clear()
    monkeypatch.setattr(Path, "read_text", tracked_read)
    try:
        rows = [{"name": "Causa", "count": 1, "total_weight_g": "100"}]
        for _ in range(3):
            figure = ranking_chart(rows, "Por causa")
            assert figure.data[0].marker.color == "#64D6A0"
            monthly_chart([{"period": "2026-11", "label": "nov 2026", "count": 1, "total_weight_g": "100"}])
            origin({"by_source": [{"source": "manual", "count": 1, "total_weight_g": "100"}]}, "kg")
        assert reads == ["theme.css", "dashboard.css"]
    finally:
        tokens.cache_clear()
