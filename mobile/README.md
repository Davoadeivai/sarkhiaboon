# اپلیکیشن موبایل سرخیابون

Expo SDK 58 (React Native 0.88) + TypeScript + Expo Router. یک کد برای اندروید، iOS و (برای تست) وب.
توضیح کامل طراحی و ساخت: `docs/DEVELOPMENT_LOG.md` بخش ۷.

## اجرا

```bash
npm install
cp .env.example .env        # EXPO_PUBLIC_API_URL — روی گوشی واقعی، IP لپ‌تاپ در شبکه
npx expo start              # Expo Go: کد QR را اسکن کنید
npx tsc --noEmit            # بررسی نوع‌ها
```

سرور برای گوشی واقعی: `python manage.py runserver 0.0.0.0:8000` و IP لپ‌تاپ در `DJANGO_ALLOWED_HOSTS`.

## تست خودکار مسیر کامل (روی نسخه‌ی وب)

```bash
# ۱) سرور با تنظیمات توسعه
cd ../backend
DJANGO_DEBUG=true CELERY_TASK_ALWAYS_EAGER=true CORS_ALLOWED_ORIGINS=http://localhost:8081 \
PAYMENT_RESULT_URL=http://localhost:8081/payment/result python manage.py runserver > server.log 2>&1 &

# ۲) ساخت و سرو نسخه‌ی وب روی پورت 8081 (با بازگشت مسیرها به index.html)
cd ../mobile
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000 npx expo export --platform web
npx serve dist -s -l 8081 &

# ۳) اجرای مسیر (Playwright پایتون) — یک عکس تمام‌قد لازم است
python scripts/web_journey.py ./shots ../backend/server.log ./portrait.jpg
```

## ساختار

| مسیر | محتوا |
|---|---|
| `src/app/` | صفحه‌ها (هر فایل یک صفحه) |
| `src/components/` | طاق و آینه، کارت محصول، دکمه‌ها، فرم، آیکون‌ها |
| `src/lib/` | ارتباط با سرور، نشست، قالب‌بندی فارسی، عکس، پرداخت |
| `src/theme/tokens.ts` | رنگ، قلم، اندازه‌ها |
