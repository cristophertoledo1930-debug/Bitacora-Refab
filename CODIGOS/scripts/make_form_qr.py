"""Generate station-specific Google Forms QR assets without network access."""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import qrcode
from qrcode.image.svg import SvgPathImage


def prefilled_url(url: str, station_code: str, entry_id: str | None = None) -> str:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "docs.google.com"
            or not re.fullmatch(r"/forms/d/(?:e/)?[A-Za-z0-9_-]+/viewform", parts.path)
            or parts.fragment):
        raise ValueError("Use URL completa HTTPS de docs.google.com/forms/.../viewform.")
    if not station_code.strip() or len(station_code) > 100:
        raise ValueError("Código de estación obligatorio (hasta 100 caracteres).")
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    if entry_id is None:
        entries = [(key, value) for key, value in pairs if re.fullmatch(r"entry\.\d+", key)]
        matching = [key for key, value in entries if value == station_code]
        if len(matching) != 1:
            raise ValueError("Indique --entry-id real o URL prefijada para esta estación.")
        entry = matching[0]
    else:
        if not re.fullmatch(r"\d+", entry_id):
            raise ValueError("entry-id debe ser numérico.")
        entry = "entry." + entry_id
    pairs = [(key, value) for key, value in pairs if key not in {entry, "usp"}]
    pairs += [("usp", "pp_url"), (entry, station_code)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), ""))


def make_form_qr(url: str, station_code: str, entry_id: str | None = None,
                 output_dir: Path = Path("storage/qr")) -> dict:
    target = prefilled_url(url, station_code, entry_id)
    # Retain a readable prefix and a digest, safely bounded for Windows filenames.
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", station_code).strip("_")[:30] or "station"
    stem = "form_" + slug + "_" + hashlib.sha256(station_code.encode("utf-8")).hexdigest()[:16]
    output_dir.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(target)
    qr.make(fit=True)
    bitmap = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    label = "Re-Fab / Lab881 · " + station_code
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default(size=18)
    # Size canvas to retain readable station labels without intruding on quiet zone.
    label_width = int(ImageDraw.Draw(bitmap).textlength(label, font=font)) + 32
    width = max(bitmap.width, label_width)
    canvas = Image.new("RGB", (width, bitmap.height + 52), "white")
    canvas.paste(bitmap, ((width - bitmap.width) // 2, 0))
    ImageDraw.Draw(canvas).text((width // 2, bitmap.height + 26), label,
                               font=font, fill="black", anchor="mm")
    metadata = PngInfo()
    metadata.add_text("form_url", target)
    metadata.add_text("station_code", station_code)
    paths = {ext: output_dir / (stem + "." + ext) for ext in ("png", "svg", "txt")}
    canvas.save(paths["png"], pnginfo=metadata)
    buffer = BytesIO()
    qr.make_image(image_factory=SvgPathImage).save(buffer)
    root = ET.fromstring(buffer.getvalue())
    viewbox = [float(v) for v in root.attrib["viewBox"].split()]
    svg_width, svg_height = viewbox[2:]
    # Expand for the caption; preserve all QR modules and four-module quiet zone.
    svg_label_width = max(svg_width, len(label) * 1.5 + 8)
    root.set("viewBox", f"0 0 {svg_label_width} {svg_height + 12}")
    root.set("width", f"{svg_label_width}mm")
    root.set("height", f"{svg_height + 12}mm")
    ns = "{http://www.w3.org/2000/svg}"
    bg = ET.Element(ns + "rect", {"width": "100%", "height": "100%", "fill": "white"})
    root.insert(0, bg)
    for child in list(root)[1:]:
        child.set("transform", f"translate({(svg_label_width - svg_width) / 2}, 0)")
    text = ET.SubElement(root, ns + "text", {"x": str(svg_label_width / 2),
        "y": str(svg_height + 7), "font-size": "3.5", "font-family": "sans-serif", "text-anchor": "middle"})
    text.text = label
    desc = ET.SubElement(root, ns + "desc")
    desc.text = target
    ET.ElementTree(root).write(paths["svg"], encoding="utf-8", xml_declaration=True)
    paths["txt"].write_text(target + "\n", encoding="utf-8")
    return {"url": target, **paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--station-code", required=True)
    parser.add_argument("--entry-id")
    parser.add_argument("--output-dir", type=Path, default=Path("storage/qr"))
    args = parser.parse_args()
    try:
        assets = make_form_qr(args.url, args.station_code, args.entry_id, args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    for kind in ("png", "svg", "txt"):
        print(assets[kind])


if __name__ == "__main__":
    main()
