# راهنمای راه‌اندازی سرخیابون روی سرور

> هدف: با دسترسی SSH به سرور کارفرما، کل سرور سرخیابون (API، پنل مدیریت، پرو مجازی، پرداخت) در یک جلسه با HTTPS بالا بیاید.
> فایل‌ها: `deploy/` (Docker Compose نسخه‌ی اصلی، nginx، گواهی SSL، پشتیبان‌گیری).

## چه چیزی تست شده و چه چیزی نه

| مورد | وضعیت |
|---|---|
| تنظیمات nginx (HTTPS، هدایت HTTP، فایل‌های static و media، هدرهای حریم خصوصی) | ✅ با nginx واقعی و گواهی آزمایشی اجرا شد |
| سرور با `DEBUG=false` روی PostgreSQL + Redis + Celery واقعی + gunicorn پشت nginx | ✅ مسیر کامل مشتری: **۲۷ از ۲۷ بررسی موفق** |
| همه‌ی ۱۲۹ تست خودکار روی PostgreSQL | ✅ |
| فایل Compose (`docker compose config`) و اسکریپت‌ها (بررسی نحو) | ✅ |
| ساخت و اجرای خود ایمیج‌های Docker و گرفتن گواهی واقعی Let's Encrypt | ❌ در محیط توسعه دسترسی به Docker Hub نبود؛ اولین اجرا روی سرور کارفرما انجام می‌شود |

## ۱. پیش‌نیازها

- **سرور:** Ubuntu 22.04 یا 24.04؛ حداقل ۲ هسته، ۴ گیگ RAM، ۴۰ گیگ دیسک.
- **دامنه:** یک رکورد A برای زیردامنه‌ی API (مثلاً `api.sarkhiaboon.ir`) که به IP سرور اشاره کند. پورت‌های ۸۰ و ۴۴۳ باز باشند.
- **دسترسی:** SSH با کاربری که sudo دارد.

## ۲. نصب Docker روی سرور ایرانی

Docker Hub و بخشی از مخازن خارجی به IP ایران سرویس نمی‌دهند. دو کار لازم است:

1. نصب Docker: اگر `curl -fsSL https://get.docker.com | sh` کار نکرد، از مخزن آینه‌ی شرکت میزبان یا بسته‌ی `docker.io` خود اوبونتو استفاده کنید (`apt install docker.io docker-compose-v2`).
2. آینه‌ی Docker Hub در `/etc/docker/daemon.json` (آدرس آینه را از شرکت میزبان بپرسید؛ مثلاً آینه‌ی آروان):
   ```json
   { "registry-mirrors": ["https://docker.arvancloud.ir"] }
   ```
   سپس `sudo systemctl restart docker` و آزمایش با `docker pull redis:7-alpine`.
3. اگر سرور به pypi.org دسترسی ندارد، آدرس آینه‌ی PyPI را در `.env` بنویسید: `PIP_INDEX_URL=https://<آینه>/simple`.

## ۳. دریافت کد

مخزن خصوصی است؛ یکی از این دو راه:
- **Deploy key:** روی سرور `ssh-keygen -t ed25519`، کلید عمومی را در GitHub ← Settings ← Deploy keys (فقط خواندنی) اضافه کنید، سپس `git clone git@github.com:Davoadeivai/sarkhiaboon.git`.
- **کپی مستقیم:** روی لپ‌تاپ `git archive -o sark.tar.gz HEAD` و انتقال با `scp`.

## ۴. تنظیم `.env`

```bash
cd sarkhiaboon && cp .env.example .env && nano .env
```

| متغیر | مقدار |
|---|---|
| `DOMAIN`، `LETSENCRYPT_EMAIL` | دامنه‌ی API و ایمیل برای گواهی SSL |
| `DJANGO_SECRET_KEY` | رشته‌ی تصادفی بلند: `python3 -c "import secrets;print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS`، `DJANGO_CSRF_TRUSTED_ORIGINS`، `PUBLIC_BASE_URL` | همان دامنه (دو مورد آخر با `https://`) |
| `POSTGRES_PASSWORD` | رمز قوی |
| `PAYMENT_CALLBACK_URL` | `https://<دامنه>/api/v1/orders/payment/callback/` |
| `TRUSTED_PROXY_COUNT` | `1` (پشت nginx) |
| پیامک، درگاه، موتور پرو | پس از دریافت اطلاعات از کارفرما؛ تا آن موقع Console/Sandbox/Mock |

`.env` را هرگز در گیت قرار ندهید.

## ۵. اجرا

```bash
./deploy/init-ssl.sh                     # فقط بار اول: گواهی HTTPS (برای آزمایش: --staging)
./deploy/prod.sh up -d --build           # کل سرویس‌ها
./deploy/prod.sh exec api python manage.py createsuperuser
./deploy/prod.sh ps                      # همه باید Up باشند
curl https://<دامنه>/health/             # {"status": "ok", "database": true}
```

پنل مدیریت: `https://<دامنه>/admin/`

**ورود اطلاعات فروشگاه** (فایل اکسل کارفرما و پوشه‌ی عکس‌ها را با scp به `backend/` منتقل کنید):
```bash
./deploy/prod.sh run --rm -v "$PWD/backend/import:/import" api \
  python manage.py import_catalog /import/catalog.xlsx --images /import/images --dry-run   # فقط بررسی
# بدون --dry-run برای ورود نهایی
```

**اپ موبایل:** در ساخت نسخه‌ی نهایی، `EXPO_PUBLIC_API_URL=https://<دامنه>` تنظیم شود.

پس از اطمینان از کارکرد HTTPS، در `.env` مقدار `DJANGO_HSTS_SECONDS=31536000` را بگذارید و `./deploy/prod.sh up -d` بزنید.

## ۶. به‌روزرسانی

```bash
git pull && ./deploy/prod.sh up -d --build
```
migrate و collectstatic هنگام بالا آمدن API خودکار اجرا می‌شوند.

## ۷. پشتیبان‌گیری و بازگردانی

- سرویس `backup` هر شب ساعت `BACKUP_HOUR` از پایگاه داده نسخه‌ی پشتیبان می‌گیرد (`deploy/backups/db-*.dump`، نگهداری `BACKUP_KEEP_DAYS` روز)، و جمعه‌ها از عکس‌های کاتالوگ.
- **عکس‌های مشتری‌ها عمداً پشتیبان‌گیری نمی‌شوند** (حریم خصوصی؛ خودکار حذف می‌شوند).
- نسخه‌ی پشتیبان دستی: `./deploy/prod.sh exec backup sh /backup.sh`
- **حتماً** پوشه‌ی `deploy/backups/` را مرتب به جای دیگری (سرور دوم یا فضای ابری) منتقل کنید؛ پشتیبان روی همان سرور در برابر خرابی دیسک کمکی نمی‌کند.
- بازگردانی:
  ```bash
  ./deploy/prod.sh exec -T backup sh -c 'pg_restore --clean --if-exists -d "$PGDATABASE"' < deploy/backups/db-YYYYMMDD-HHMM.dump
  ```

## ۸. سرور واسط خارجی (برای موتور پرو)

اگر سرور ایرانی است و اتصال به RunPod قطع و وصل می‌شود، در `.env`:
```
HTTPS_PROXY=http://<سرور-واسط>:<پورت>
NO_PROXY=localhost,127.0.0.1,db,redis,api,<دامنه‌ی درگاه بانک>,<دامنه‌ی سامانه‌ی پیامک>
```
**درگاه بانکی و پیامک باید مستقیم از IP ایران فراخوانی شوند**؛ دامنه‌ی آن‌ها حتماً در `NO_PROXY` باشد.

## ۹. عیب‌یابی

| مشکل | بررسی |
|---|---|
| سایت بالا نمی‌آید | `./deploy/prod.sh ps` و `./deploy/prod.sh logs --tail 100 api nginx` |
| پرو در صف می‌ماند | `./deploy/prod.sh logs --tail 100 worker` |
| کد پیامکی نمی‌رسد | لاگ api؛ در حالت Console، کد در همین لاگ چاپ می‌شود |
| خطای گواهی | DNS دامنه، باز بودن پورت ۸۰، سپس `./deploy/init-ssl.sh --staging` برای آزمایش |
| خطای 413 در آپلود عکس | `client_max_body_size` در `deploy/nginx/templates/default.conf.template` |
