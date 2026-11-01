# سرخیابون — اپلیکیشن پرو مجازی لباس

- `backend/` — سرور: Django + Django REST Framework، صف پردازش Celery، موتور پرو مجازی قابل‌تعویض
- `mobile/` — اپلیکیشن اندروید و iOS: Expo (React Native) + TypeScript

**مستندات کامل فنی و دفترچه‌ی ساخت:** [`docs/DEVELOPMENT_LOG.md`](docs/DEVELOPMENT_LOG.md)

## اجرای سریع (توسعه)

```bash
cd backend
pip install -r requirements.txt
export DJANGO_DEBUG=true CELERY_TASK_ALWAYS_EAGER=true
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

- مستندات API: http://127.0.0.1:8000/api/docs/
- پنل مدیریت: http://127.0.0.1:8000/admin/

## اجرای اپلیکیشن موبایل

```bash
cd mobile
npm install
cp .env.example .env    # نشانی سرور
npx expo start         # کد QR را با Expo Go اسکن کنید
```

## تست‌ها

```bash
cd backend
DJANGO_DEBUG=true python manage.py test                  # ۱۱۴ تست خودکار
python scripts/smoke_test.py --base http://127.0.0.1:8000 --log server.log   # بررسی زنده‌ی سرتاسری
```

## اجرای کامل با Docker

```bash
cp .env.example .env    # ویرایش مقادیر
docker compose up --build -d
```

## ساختار

| مسیر | محتوا |
|---|---|
| `backend/apps/accounts` | ورود با موبایل و کد پیامکی، کاربر مهمان |
| `backend/apps/catalog` | محصولات، دسته‌بندی، بنر، آیکون تبلیغاتی، علاقه‌مندی |
| `backend/apps/tryon` | موتور پرو مجازی (آزمایشی / RunPod) |
| `backend/apps/orders` | سبد خرید، سفارش، پرداخت (آزمایشی / زرین‌پال) |
| `mobile/src/app` | صفحه‌های اپ (ویترین، دسته‌ها، محصول، پرو، کمد، سبد، خرید، سفارش‌ها) |
| `mobile/src/theme/tokens.ts` | رنگ، قلم و اندازه‌های طراحی |
| `docs/` | مستندات فنی |
