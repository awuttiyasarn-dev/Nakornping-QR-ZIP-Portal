#!/usr/bin/env python3
"""Nakornping QR ZIP Portal
1) รวมไฟล์ Word ใน word_files/ -> files.zip
2) สร้าง qr.png (ชี้ไปที่ files.zip บน GitHub)
3) สร้างหน้าเว็บ portal/index.html (มี QR + ปุ่มดาวน์โหลด) สำหรับ GitHub Pages
รัน: python make_qr.py
"""
import argparse, base64, html, io, os, zipfile
from datetime import datetime
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M

WORD_EXT = {".docx", ".doc", ".dotx", ".docm"}
DEFAULT_REPO = "awuttiyasarn-dev/Nakornping-QR-ZIP-Portal"

PAGE = """<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nakornping QR ZIP Portal</title>
<style>
body{font-family:system-ui,"Noto Sans Thai",sans-serif;background:#f3f6fa;margin:0;
display:flex;min-height:100vh;align-items:center;justify-content:center;color:#1f2937}
.card{background:#fff;border-radius:16px;padding:28px;max-width:420px;width:90%;
box-shadow:0 6px 24px rgba(0,0,0,.08);text-align:center}
img{width:100%;max-width:300px;image-rendering:pixelated}
a.btn{display:inline-block;margin-top:14px;background:#2563eb;color:#fff;
padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:600}
ul{text-align:left;font-size:14px;color:#4b5563;max-height:160px;overflow:auto}
small{color:#6b7280}
</style></head><body><div class="card">
<h2>ดาวน์โหลดไฟล์ Word (.zip)</h2>
<img src="data:image/png;base64,__QR__" alt="QR Code">
<p>สแกน QR หรือกดปุ่มด้านล่าง</p>
<a class="btn" href="__URL__">⬇ ดาวน์โหลด files.zip</a>
<p><b>ไฟล์ในชุดนี้ (__N__ ไฟล์)</b></p>
<ul>__LIST__</ul>
<small>อัปเดตล่าสุด __DATE__</small>
</div></body></html>"""


def make_zip(src: Path, out: Path):
    files = sorted(p for p in src.rglob("*")
                   if p.is_file() and p.suffix.lower() in WORD_EXT
                   and not p.name.startswith("~$"))
    if not files:
        raise SystemExit(f"ไม่พบไฟล์ Word ใน '{src}/' — วางไฟล์ .docx ก่อน")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.relative_to(src))
    return [f.relative_to(src).as_posix() for f in files]


def make_qr_image(url: str):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=12, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", DEFAULT_REPO))
    ap.add_argument("--branch", default="main")
    ap.add_argument("--src", default="word_files")
    a = ap.parse_args()

    names = make_zip(Path(a.src), Path("files.zip"))
    url = f"https://github.com/{a.repo}/raw/{a.branch}/files.zip"

    img = make_qr_image(url)
    img.save("qr.png")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    page = (PAGE.replace("__QR__", qr_b64).replace("__URL__", url)
            .replace("__N__", str(len(names)))
            .replace("__LIST__", "".join(f"<li>{html.escape(n)}</li>" for n in names))
            .replace("__DATE__", datetime.now().strftime("%Y-%m-%d %H:%M")))
    Path("portal").mkdir(exist_ok=True)
    Path("portal/index.html").write_text(page, encoding="utf-8")

    print(f"zip: {len(names)} ไฟล์ -> files.zip")
    print(f"ลิงก์: {url}")
    print("สร้าง qr.png และ portal/index.html แล้ว")


if __name__ == "__main__":
    main()
