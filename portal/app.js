
"use strict";

const CONFIG = {
  GAS_WEB_APP_URL:
    "https://script.google.com/macros/s/PUT_YOUR_DEPLOYMENT_ID/exec",

  MANIFEST_URL: "./files.json",

  ALLOWED_HOST: "github.com"
};

let files = [];

document.addEventListener("DOMContentLoaded", initialize);


/**
 * INITIALIZE
 */
async function initialize() {
  const search = document.getElementById("searchInput");

  if (search) {
    search.addEventListener("input", filterFiles);
  }

  await loadFiles();
}


/**
 * LOAD FILES.JSON
 */
async function loadFiles() {
  setStatus("กำลังโหลดรายการไฟล์...");

  try {
    const response = await fetch(
      CONFIG.MANIFEST_URL + "?t=" + Date.now(),
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error("ไม่สามารถโหลด files.json");
    }

    const manifest = await response.json();

    if (!Array.isArray(manifest.files)) {
      throw new Error("รูปแบบ Manifest ไม่ถูกต้อง");
    }

    files = manifest.files;

    renderFiles(files);

  } catch (error) {
    setStatus("ไม่สามารถโหลดรายการไฟล์ได้");
    showMessage(error.message, true);
  }
}


/**
 * FILE FIELD HELPERS
 */
function fileId(file) {
  return String(file.id || file.file_id || "");
}

function fileName(file) {
  return String(
    file.name ||
    file.file_name ||
    file.filename ||
    "Unnamed ZIP"
  );
}

function downloadUrl(file) {
  return String(
    file.download_url ||
    file.browser_download_url ||
    ""
  );
}

function fileSize(file) {
  const size = Number(file.size || file.size_bytes || 0);

  if (!size) return "ไม่ระบุขนาด";

  if (size < 1024 ** 2) {
    return (size / 1024).toFixed(1) + " KB";
  }

  return (size / 1024 ** 2).toFixed(2) + " MB";
}


/**
 * RENDER FILES
 */
function renderFiles(items) {
  const container = document.getElementById("fileList");

  if (!container) return;

  container.replaceChildren();

  setStatus("พบไฟล์ " + items.length + " รายการ");

  if (!items.length) {
    setStatus("ไม่พบรายการไฟล์");
    return;
  }

  items.forEach(file => {
    const card = document.createElement("div");
    card.className = "file";

    const icon = document.createElement("div");
    icon.className = "file-icon";
    icon.textContent = "🗜️";

    const info = document.createElement("div");
    info.className = "file-info";

    const name = document.createElement("div");
    name.className = "file-name";
    name.textContent = fileName(file);

    const meta = document.createElement("div");
    meta.className = "file-meta";
    meta.textContent = "ZIP File • " + fileSize(file);

    info.append(name, meta);

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "⬇ ดาวน์โหลด";

    button.addEventListener("click", () => {
      downloadFile(file, button);
    });

    card.append(icon, info, button);
    container.appendChild(card);
  });
}


/**
 * SEARCH
 */
function filterFiles() {
  const keyword = document
    .getElementById("searchInput")
    .value
    .trim()
    .toLowerCase();

  const result = files.filter(file =>
    fileName(file).toLowerCase().includes(keyword)
  );

  renderFiles(result);
}


/**
 * VALIDATE GITHUB RELEASE URL
 */
function validateUrl(value) {
  try {
    const url = new URL(value);

    return (
      url.protocol === "https:" &&
      url.hostname === CONFIG.ALLOWED_HOST &&
      /^\/[^/]+\/[^/]+\/releases\/download\/[^/]+\/[^/]+$/
        .test(url.pathname)
    );

  } catch {
    return false;
  }
}


/**
 * DOWNLOAD
 */
async function downloadFile(file, button) {
  const id = fileId(file);
  const name = fileName(file);
  const url = downloadUrl(file);

  if (!id) {
    showMessage("ไม่พบ File ID", true);
    return;
  }

  if (!validateUrl(url)) {
    showMessage("GitHub Release URL ไม่ถูกต้อง", true);
    return;
  }

  if (
    !CONFIG.GAS_WEB_APP_URL.endsWith("/exec") ||
    CONFIG.GAS_WEB_APP_URL.includes("PUT_YOUR_DEPLOYMENT_ID")
  ) {
    showMessage("กรุณาตั้งค่า GAS Web App URL", true);
    return;
  }

  button.disabled = true;
  button.textContent = "กำลังบันทึกข้อมูล...";

  const payload = {
    file_id: id,
    file_name: name,
    download_url: url,
    user_agent: navigator.userAgent,
    referrer: document.referrer
  };

  try {
    /*
     * ส่ง log แบบ no-cors
     * Browser จะไม่สามารถอ่าน response ได้
     */

    await fetch(CONFIG.GAS_WEB_APP_URL, {
      method: "POST",
      mode: "no-cors",
      redirect: "follow",
      headers: {
        "Content-Type": "text/plain;charset=utf-8"
      },
      body: JSON.stringify(payload)
    });

    button.textContent = "กำลังเปิดไฟล์...";

    showMessage("กำลังเปลี่ยนไปยัง GitHub Releases");

    setTimeout(() => {
      window.location.assign(url);
    }, 700);

  } catch (error) {
    button.disabled = false;
    button.textContent = "⬇ ดาวน์โหลด";

    showMessage(
      "ไม่สามารถส่งข้อมูลบันทึกได้ กรุณาลองอีกครั้ง",
      true
    );
  }
}


/**
 * STATUS
 */
function setStatus(message) {
  const element = document.getElementById("status");

  if (element) {
    element.textContent = message;
  }
}


/**
 * MESSAGE
 */
function showMessage(message, isError = false) {
  const element = document.getElementById("message");

  if (!element) {
    alert(message);
    return;
  }

  element.textContent = message;
  element.classList.remove("hidden", "error");

  if (isError) {
    element.classList.add("error");
  }
}
