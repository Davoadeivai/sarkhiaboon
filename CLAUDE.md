# CLAUDE.md — سرخیابون (Sarkhiaboon)

Virtual clothing try-on (پرو مجازی لباس) shopping app for client **Mr. Ebrahimi**.
Developer: Davoad Eivazkhani (freelance, Tehran). Talk to Davoad in **Persian** unless he writes in English.

Read these before doing any work:
1. `docs/PROJECT_CONTEXT.md` — business context: agreements, scope, price, client decisions, open questions (Persian).
2. `docs/DEVELOPMENT_LOG.md` — full technical build log of the backend (Persian). **Every part you build gets a section added here**, with complete explanation (files, decisions and why, endpoints, tests, known limits). This is a standing requirement from Davoad.

## Status
- **Backend: done and verified** (Django API — accounts, catalog, try-on, orders/payment). 114 tests pass, live e2e journey 24/24, OpenAPI schema clean (`--fail-on-warn`).
- **Next:** (a) GPU worker: CatVTON Docker image for RunPod Serverless, (b) mobile app (React Native, Android + iOS), (c) client-doc updates once path 2 is confirmed (see PROJECT_CONTEXT).
- Not yet done: Docker stack never actually run; RunPod / Kavenegar / Zarinpal only tested against mocked HTTP; blur threshold needs calibration on real photos; shoes unsupported by engine.

## Layout
```
backend/            Django project (manage.py here)
  config/           settings (all config from env vars), urls, celery
  apps/core         base model, pagination, exception handler, OptionalJWTAuthentication, testing helpers
  apps/accounts     phone + OTP login, guest users, guest→user merge (signal `guest_merged`)
  apps/catalog      categories, products, variants, banners, home shortcuts (ad icons), favorites, seed_demo
  apps/tryon        person photos, try-on jobs, swappable providers (mock / RunPod), quotas, cache
  apps/orders       cart, addresses, checkout (stock reservation), payment gateways (sandbox / Zarinpal)
  scripts/smoke_test.py   live HTTP end-to-end journey
docs/               DEVELOPMENT_LOG.md, PROJECT_CONTEXT.md, client/ (proposals, roadmap, contract — PDF+DOCX)
tools/docs/         scripts used to generate the Persian RTL client documents
```

## Commands (run from `backend/`)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_DEBUG=true CELERY_TASK_ALWAYS_EAGER=true # Windows PowerShell: $env:DJANGO_DEBUG="true"; $env:CELERY_TASK_ALWAYS_EAGER="true"
python manage.py migrate && python manage.py seed_demo
python manage.py runserver                              # API docs: /api/docs/  admin: /admin/
python manage.py test                                   # must stay green
python manage.py spectacular --file schema.yml --validate --fail-on-warn
python scripts/smoke_test.py --base http://127.0.0.1:8000 --log server.log
```
Full stack: `cp .env.example .env && docker compose up --build` (api, worker, beat, postgres, redis).

## Conventions (keep them)
- Python 3.11, Django 5.1, DRF, simplejwt, Celery+Redis. PostgreSQL if `POSTGRES_DB` set, else SQLite.
- API under `/api/v1/`. Code identifiers/comments in English; every user-facing message in Persian.
- No secrets in code — everything via env vars; add new ones to `.env.example`.
- External services are **swappable by dotted path in settings**: `TRYON["PROVIDER"]`, `SMS_BACKEND`, `PAYMENT_GATEWAY`. Add new engines as new classes, don't branch inside existing ones.
- Prices are integer **Toman**; Zarinpal receives Rial (×10).
- Tests use `apps.core.testing.APITestBase` (clears cache, patches throttle rates, temp MEDIA_ROOT), `EagerCeleryMixin`, `tryon_settings(...)`, catalog factories in `apps/catalog/testing.py`. Add tests with every feature; run the full suite and the schema check before calling anything done.
- Privacy: person photos stripped of EXIF/GPS, random filenames, auto-deleted (`PERSON_PHOTO_RETENTION_HOURS`), never previewed in admin.

## GPU worker contract (what the RunPod handler must return)
Input sent by `apps/tryon/providers/runpod.py`: `{"input": {"person_image": <base64 JPEG>, "garment_image": <base64>, "category": "upper_body|lower_body|dresses", "job_id": "<uuid>"}}`.
Output: `{"image": "<base64>", "format": "png"}` on success, or `{"error": "<message>"}`. See DEVELOPMENT_LOG §4 (بخش ۴ — اتصال به RunPod) for exact fields, timeouts and retry behaviour. Server already records RunPod `delayTime`/`executionTime`.

## Mobile app notes (for when it starts)
- Deep link scheme `sarkhiaboon://` — payment result returns to `sarkhiaboon://payment/result`.
- Home screen is one call: `GET /api/v1/catalog/home/`. Try-on: upload photo → create job (202, or 200 from cache) → poll job. Guest login first, OTP login later merges guest data.
- UI fully RTL Persian.

## Client documents (Persian)
- Must be fully **right-aligned RTL**, font **Vazirmatn**; headings/bullets use alignment START, body JUSTIFIED; sectPr gets `<w:bidi/>` (see `tools/docs/patch_rtl.py`). No explicit page breaks.
- Only **one** version of each document (no alternate versions).
- When Davoad asks for messages to the client without prices: say only that costs increase as items are added.
