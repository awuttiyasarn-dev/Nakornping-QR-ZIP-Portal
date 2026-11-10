# Nakornping QR ZIP Portal

สแกน QR -> ดาวน์โหลดไฟล์ Word (.zip) ใช้ GitHub + Python เท่านั้น

## ใช้งาน
1. วางไฟล์ `.docx` ไว้ในโฟลเดอร์ `word_files/`
2. Push ขึ้น GitHub -> Actions สร้าง `files.zip`, `qr.png`, `portal/index.html` ให้อัตโนมัติ
3. (ถ้าต้องการหน้าเว็บ) Settings > Pages > Deploy from branch > `main` / root
   หน้าเว็บ: https://awuttiyasarn-dev.github.io/Nakornping-QR-ZIP-Portal/portal/

## ตั้งค่าครั้งแรก
- Settings > Actions > General > Workflow permissions = **Read and write**
- Repo ต้องเป็น **Public**

## รันในเครื่อง
```bash
pip install -r requirements.txt
python make_qr.py
```
