"""
End-to-end check of the whole customer journey on the web build of the app,
against a running Django server (mock try-on engine, sandbox payment, console SMS).
Serve the web build on :8081 with SPA fallback first (see mobile/README.md).
"""
import asyncio, json, re, sys
from playwright.async_api import async_playwright
# usage: python web_journey.py <screenshot-dir> <django-server.log> <portrait.jpg>
OUT, SERVER_LOG, PHOTO = sys.argv[1], sys.argv[2], sys.argv[3]
APP = 'http://localhost:8081'
PHONE = '09121234567'

def otp_from_log():
    txt = open(SERVER_LOG, encoding='utf-8', errors='ignore').read()
    codes = re.findall(r'(\d{5})', txt.split(PHONE)[-1]) if PHONE in txt else []
    return codes[0] if codes else None

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, locale='fa-IR')
        page = await ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(f'PAGEERROR: {e}'))
        page.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
        async def shot(name, full=False):
            await page.wait_for_timeout(900)
            await page.screenshot(path=f'{OUT}/{name}.png', full_page=full)
            print('shot', name)

        await page.goto(APP, wait_until='networkidle'); await page.wait_for_timeout(2000)
        await shot('01-home'); await shot('01-home-full', True)

        await page.get_by_role('tab', name='دسته‌ها').click(); await page.wait_for_timeout(1500)
        await shot('02-catalog')

        # product that supports try-on
        await page.goto(f'{APP}/', wait_until='networkidle'); await page.wait_for_timeout(1500)
        await page.get_by_role('link', name=re.compile('مانتو کتان بلند')).first.click(); await page.wait_for_timeout(1500)
        await shot('03-product')
        await page.get_by_role('button', name='پرو کن').click(); await page.wait_for_timeout(1500)
        await shot('04-tryon-start')
        async with page.expect_file_chooser() as fc:
            await page.get_by_role('button', name='از گالری').click()
        chooser = await fc.value
        await chooser.set_files(PHOTO); await page.wait_for_timeout(1200)
        await shot('05-tryon-selected')
        await page.get_by_role('button', name='پرو کن').click()
        await page.wait_for_url(re.compile('/tryon/job/'), timeout=20000); await page.wait_for_timeout(2500)
        job_url = page.url
        await shot('06-tryon-result')
        await page.get_by_role('button', name='به کمد').click(); await page.wait_for_timeout(1200)
        await shot('06b-tryon-saved')

        # processing state (simulated: the dev server runs jobs instantly)
        job_id = job_url.split('/tryon/job/')[1].split('?')[0]
        async def fake(route):
            resp = await route.fetch(); data = await resp.json()
            data.update(status='queued', queue_position=2, result_image=None)
            await route.fulfill(response=resp, json=data)
        await page.route(f'**/api/v1/tryon/jobs/{job_id}/', fake)
        prev = job_url.split('preview=')[1] if 'preview=' in job_url else ''
        await page.goto(f'{APP}/tryon/job/{job_id}?preview={prev}', wait_until='domcontentloaded'); await page.wait_for_timeout(2600)
        await shot('07-tryon-queued')
        await page.unroute(f'**/api/v1/tryon/jobs/{job_id}/')

        await page.goto(f'{APP}/closet', wait_until='networkidle'); await page.wait_for_timeout(1800)
        await shot('08-closet')

        # add to cart
        await page.goto(f'{APP}/', wait_until='networkidle'); await page.wait_for_timeout(1200)
        await page.get_by_role('link', name=re.compile('مانتو کتان بلند')).first.click(); await page.wait_for_timeout(1200)
        await page.get_by_role('button', name='سایز M').click()
        await page.get_by_role('button', name='افزودن به سبد').click(); await page.wait_for_timeout(1200)
        await shot('09-product-added')
        await page.goto(f'{APP}/cart', wait_until='networkidle'); await page.wait_for_timeout(1500)
        await shot('10-cart')

        # login
        await page.get_by_role('button', name='ورود و ادامه‌ی خرید').click(); await page.wait_for_timeout(1200)
        await page.get_by_label('شماره موبایل').fill('۰۹۱۲۱۲۳۴۵۶۷')
        await shot('11-login')
        await page.get_by_role('button', name='دریافت کد').click(); await page.wait_for_timeout(1500)
        await shot('12-login-code')
        code = otp_from_log(); print('otp', code)
        await page.get_by_label('کد ورود').fill(code)
        await page.wait_for_url(re.compile('/checkout'), timeout=15000); await page.wait_for_timeout(1500)
        await shot('13-checkout-empty', True)

        if await page.get_by_label('نام گیرنده').count():
            await page.get_by_label('نام گیرنده').fill('سارا محمدی')
            await page.get_by_label('موبایل گیرنده').fill('09121234567')
            await page.get_by_label('استان').fill('تهران')
            await page.get_by_label('شهر').fill('تهران')
            await page.get_by_label('نشانی کامل').fill('خیابان لاله‌زار، کوچه‌ی سوم، پلاک ۱۲')
            await page.get_by_label('کد پستی').fill('۱۱۳۶۷-۴۵۶۷۸')
            await page.get_by_role('button', name='ذخیره‌ی نشانی').click(); await page.wait_for_timeout(1500)
        await shot('14-checkout')
        await page.get_by_role('button', name=re.compile('^پرداخت')).click()
        await page.wait_for_url(re.compile('/payment/sandbox/'), timeout=15000)
        await page.get_by_text('پرداخت موفق').click()
        await page.wait_for_url(re.compile('/payment/result'), timeout=15000); await page.wait_for_timeout(1800)
        await shot('15-payment-result')
        await page.get_by_role('button', name='پیگیری سفارش').click(); await page.wait_for_timeout(1800)
        await shot('16-order', True)
        await page.goto(f'{APP}/profile', wait_until='networkidle'); await page.wait_for_timeout(1500)
        await shot('17-profile')
        await page.goto(f'{APP}/orders', wait_until='networkidle'); await page.wait_for_timeout(1500)
        await shot('18-orders')
        await page.goto(f'{APP}/privacy', wait_until='networkidle'); await page.wait_for_timeout(1000)
        await shot('19-privacy')
        print('\n'.join(errs[:20]) or 'no console errors')
        await b.close()
asyncio.run(main())
