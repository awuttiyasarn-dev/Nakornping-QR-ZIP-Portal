
from __future__ import annotations

import os
import sys
import json
import uuid
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

import requests
import qrcode
from dotenv import load_dotenv


# ============================================================
# NAKORNPING QR ZIP DOWNLOAD PORTAL
# Version 1.0.0
# GitHub Releases + GitHub Pages + Google Sheets
# ============================================================

APP_NAME = "Nakornping QR ZIP Download Portal"
VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"

API = "https://api.github.com"
MANIFEST = "files.json"
MAX_SIZE = 2 * 1024**3

TIMEOUT = (20, 180)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv(ROOT / ".env")

CONFIG = {
    "TOKEN": os.getenv("GITHUB_TOKEN", "").strip(),
    "REPO": os.getenv("GITHUB_REPO", "").strip(),
    "PAGES_URL": os.getenv("PAGES_BASE_URL", "").strip().rstrip("/") + "/",
    "BRANCH": os.getenv("GITHUB_BRANCH", "gh-pages").strip()
}


# ============================================================
# UTILITIES
# ============================================================

def log(message, level="INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{level}] {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_config():
    if not CONFIG["TOKEN"]:
        raise ValueError("กรุณากำหนด GITHUB_TOKEN ใน .env")

    if not CONFIG["REPO"]:
        raise ValueError("กรุณากำหนด GITHUB_REPO ใน .env")

    if not CONFIG["PAGES_URL"].startswith("https://"):
        raise ValueError("PAGES_BASE_URL ไม่ถูกต้อง")

    if "/" not in CONFIG["REPO"]:
        raise ValueError("GITHUB_REPO ต้องเป็น OWNER/REPOSITORY")


# ============================================================
# GITHUB API
# ============================================================

class GitHubAPI:

    def __init__(self):

        self.repo = CONFIG["REPO"]

        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": f"Bearer {CONFIG['TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Nakornping-QR-ZIP-Portal"
        })

    def request(self, method, url, **kwargs):

        response = self.session.request(
            method,
            url,
            timeout=TIMEOUT,
            **kwargs
        )

        if not response.ok:

            try:
                error = response.json().get(
                    "message",
                    response.text
                )
            except Exception:
                error = response.text

            raise RuntimeError(
                f"GitHub API {response.status_code}: {error}"
            )

        return response

    def create_release(self, tag, title, description):

        url = f"{API}/repos/{self.repo}/releases"

        return self.request(
            "POST",
            url,
            json={
                "tag_name": tag,
                "name": title,
                "body": description,
                "draft": False,
                "prerelease": False
            }
        ).json()

    def upload_asset(self, release, path):

        upload_url = release["upload_url"].split("{", 1)[0]

        with path.open("rb") as file:

            result = self.request(
                "POST",
                upload_url,
                params={"name": path.name},
                data=file,
                headers={
                    "Content-Type": "application/zip"
                }
            )

        return result.json()

    def get_manifest(self):

        url = f"{API}/repos/{self.repo}/contents/{MANIFEST}"

        response = self.session.get(
            url,
            params={"ref": CONFIG["BRANCH"]},
            timeout=TIMEOUT
        )

        if response.status_code == 404:
            return {
                "schema_version": 1,
                "files": []
            }, None

        if not response.ok:
            raise RuntimeError(
                f"Cannot read manifest: {response.text}"
            )

        data = response.json()

        import base64

        content = base64.b64decode(
            data["content"]
        ).decode("utf-8")

        return json.loads(content), data["sha"]

    def save_manifest(self, manifest, sha=None):

        import base64

        url = f"{API}/repos/{self.repo}/contents/{MANIFEST}"

        body = {
            "message": "Update ZIP download manifest",
            "branch": CONFIG["BRANCH"],
            "content": base64.b64encode(
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")
            ).decode("ascii")
        }

        if sha:
            body["sha"] = sha

        return self.request(
            "PUT",
            url,
            json=body
        ).json()


# ============================================================
# QR CODE
# ============================================================

def create_qr(file_id):

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    url = (
        CONFIG["PAGES_URL"]
        + "?id="
        + quote(file_id)
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    path = OUTPUT / f"QR_{file_id}.png"

    image.save(path)

    return url, path


# ============================================================
# ZIP PROCESSING
# ============================================================

def process_zip(path, github, manifest):

    path = Path(path).expanduser().resolve()

    if not path.is_file():
        log(f"ไม่พบไฟล์: {path}", "ERROR")
        return False

    if path.suffix.lower() != ".zip":
        log(f"ไม่ใช่ไฟล์ ZIP: {path.name}", "WARNING")
        return False

    size = path.stat().st_size

    if size <= 0 or size >= MAX_SIZE:
        log(f"ขนาดไฟล์ไม่ถูกต้อง: {path.name}", "ERROR")
        return False

    log(f"กำลังตรวจสอบ {path.name}")

    checksum = sha256_file(path)

    # Duplicate detection
    for item in manifest["files"]:

        if item.get("sha256") == checksum:

            log(
                f"ไฟล์นี้เคยอัปโหลดแล้ว: {path.name}",
                "WARNING"
            )

            return False

    file_id = uuid.uuid4().hex[:16]

    now = datetime.now(timezone.utc)

    timestamp = now.strftime("%Y%m%d-%H%M%S")

    tag = f"zip-{timestamp}-{file_id[:6]}"

    title = path.stem

    log("กำลังสร้าง GitHub Release")

    release = github.create_release(
        tag,
        title,
        f"{APP_NAME}\nFile: {path.name}"
    )

    log("กำลังอัปโหลด ZIP")

    asset = github.upload_asset(
        release,
        path
    )

    download_url = asset.get(
        "browser_download_url"
    )

    if not download_url:
        raise RuntimeError(
            "GitHub ไม่ส่ง Direct Download URL"
        )

    record = {
        "id": file_id,
        "title": title,
        "filename": path.name,
        "size_bytes": size,
        "sha256": checksum,
        "release_tag": tag,
        "download_url": download_url,
        "created_at": now.isoformat(),
        "description": "Nakornping ZIP Download"
    }

    manifest["files"].insert(
        0,
        record
    )

    manifest["updated_at"] = now.isoformat()

    portal_url, qr_path = create_qr(file_id)

    metadata = {
        **record,
        "portal_url": portal_url,
        "release_url": release["html_url"]
    }

    metadata_path = (
        OUTPUT / f"metadata_{file_id}.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    log(f"อัปโหลดสำเร็จ: {path.name}")

    print("\n" + "=" * 55)
    print(f"FILE       : {path.name}")
    print(f"SIZE       : {size:,} bytes")
    print(f"SHA-256    : {checksum}")
    print(f"RELEASE    : {release['html_url']}")
    print(f"DOWNLOAD   : {download_url}")
    print(f"PORTAL     : {portal_url}")
    print(f"QR CODE    : {qr_path}")
    print("=" * 55)

    return True


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=APP_NAME
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="ZIP files"
    )

    parser.add_argument(
        "--folder",
        help="Import all ZIP files from folder"
    )

    args = parser.parse_args()

    print("=" * 60)
    print(f"{APP_NAME} v{VERSION}")
    print("=" * 60)

    validate_config()

    github = GitHubAPI()

    manifest, sha = github.get_manifest()

    if not isinstance(manifest.get("files"), list):
        raise ValueError("Manifest files ต้องเป็นรายการ")

    files = [
        Path(x)
        for x in args.files
    ]

    if args.folder:

        folder = Path(args.folder).expanduser()

        if not folder.is_dir():
            raise ValueError("ไม่พบโฟลเดอร์ที่ระบุ")

        files.extend(folder.glob("*.zip"))

    if not files:
        parser.print_help()
        return

    imported = 0

    for path in files:

        if process_zip(path, github, manifest):
            imported += 1

            # Persist after each successful upload.
            saved = github.save_manifest(
                manifest,
                sha
            )

            sha = saved["content"]["sha"]

            log("อัปเดต GitHub Pages Manifest สำเร็จ")

    print("\n" + "=" * 60)
    log(f"นำเข้าสำเร็จ {imported} ไฟล์")
    log(f"รายการทั้งหมด {len(manifest['files'])} ไฟล์")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        log("ยกเลิกการทำงาน", "WARNING")
        sys.exit(130)

    except Exception as error:
        log(str(error), "ERROR")
        sys.exit(1)
