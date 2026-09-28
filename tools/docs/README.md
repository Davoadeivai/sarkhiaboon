# ابزار ساخت اسناد فارسی

- `build_gpu_proposal.js` — نمونه‌ی ساخت سند Word راست‌چین با docx-js (`npm i docx` سپس `node build_gpu_proposal.js`)
- `patch_rtl.py` — افزودن `<w:bidi/>` به sectPr فایل docx تا کل سند راست‌به‌چپ شود
- `render.py` + `doc.css` — تبدیل `docs/DEVELOPMENT_LOG.md` به PDF (pandoc + Playwright Chromium، CSS راست‌چین)
- فونت لازم: Vazirmatn (https://github.com/rastikerdar/vazirmatn/releases)
- تبدیل docx به PDF: `soffice --headless --convert-to pdf file.docx`

قواعد: تیتر و بولت با تراز START، متن بدنه JUSTIFIED، بدون page break صریح، فقط یک نسخه از هر سند.
