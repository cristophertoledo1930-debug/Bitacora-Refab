"""Execute the approved palette check and verify text contrast independently."""
import importlib.util
from pathlib import Path
import subprocess
import sys

from lab_hub.dashboard.components import tokens


def test_approved_palette_and_text_contrast():
    root = Path(__file__).resolve().parents[1]
    script = root / ".agents/skills/dataviz/scripts/validate_palette.py"
    colors = tokens()
    assert [colors[f"series-{i}"] for i in (1, 2, 3)] == ["#199E70", "#3987E5", "#D95926"]
    args = [sys.executable, "-X", "utf8", str(script), "#199e70,#3987e5,#d95926",
            "--mode", "dark", "--surface", "#14231D", "--pairs", "all"]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    output = root / "docs/redesign/codex/evidencias"
    output.mkdir(exist_ok=True)
    (output / "palette.txt").write_text(result.stdout, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ALL CHECKS PASS" in result.stdout
    spec = importlib.util.spec_from_file_location("palette_validator", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ratios = {}
    for foreground in ("text", "muted", "danger", "warn", "primary"):
        for background in ("bg", "panel", "input"):
            ratio = module.contrast(colors[foreground], colors[background])
            assert ratio >= 4.5, (foreground, background, ratio)
            ratios[f"{foreground}/{background}"] = round(ratio, 2)
    import json
    (output / "contrast.json").write_text(json.dumps(ratios, indent=2), encoding="utf-8")
