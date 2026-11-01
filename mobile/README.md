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

## اجرا روی گوشی واقعی

**۱) سرور روی لپ‌تاپ، قابل دسترس از شبکه‌ی Wi-Fi:**

```bash
cd ../backend
# IP لپ‌تاپ: ویندوز ipconfig / مک ipconfig getifaddr en0 — مثلاً 192.168.1.10
DJANGO_DEBUG=true CELERY_TASK_ALWAYS_EAGER=true DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10 \
python manage.py runserver 0.0.0.0:8000
```

**۲) اپ:** در `mobile/.env` بنویسید `EXPO_PUBLIC_API_URL=http://192.168.1.10:8000` و سپس `npx expo start`.
گوشی و لپ‌تاپ باید روی یک Wi-Fi باشند (اگر نشد: `npx expo start --tunnel`).

**۳) گوشی:** برنامه‌ی **Expo Go** (نسخه‌ی سازگار با SDK 58) را نصب و کد QR را اسکن کنید — اندروید با خود Expo Go، آیفون با دوربین.
بار اول اپ یک‌بار خودش را برای راست‌به‌چپ شدن دوباره بارگذاری می‌کند.

> در Expo Go برگشت خودکار از بانک به اپ کار نمی‌کند (طرح `sarkhiaboon://` فقط در نسخه‌ی ساخته‌شده هست)؛ صفحه‌ی بانک را ببندید، اپ به صفحه‌ی سفارش می‌رود و وضعیت پرداخت را نشان می‌دهد.

**فایل نصبی اندروید (APK)** — بدون Expo Go، با همه‌ی امکانات (حساب رایگان expo.dev لازم است):

```bash
npx eas-cli@latest login
npx eas-cli@latest build -p android --profile development   # APK برای تست؛ لینک دانلود می‌دهد
```

**آیفون بدون Expo Go:** نیازمند حساب Apple Developer (۹۹ دلار در سال) و `eas build -p ios`؛ یا روی مک با Xcode: `npx expo run:ios --device`.

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
