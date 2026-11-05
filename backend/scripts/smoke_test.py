"""
End-to-end smoke test: drives a running server over real HTTP through the
whole customer journey (guest, photo, try-on, cache, OTP login, cart,
address, checkout, sandbox payment, deep link back to the app).

Requirements on the server under test:
  SMS_BACKEND=ConsoleSMSBackend (the OTP is read from the server log),
  PAYMENT_GATEWAY=SandboxGateway, demo data loaded (manage.py seed_demo).

Usage:
  python scripts/smoke_test.py --base http://127.0.0.1:8000 --log /path/to/server.log
"""
import argparse
import io
import re
import sys
import time

import requests
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument("--base", default="http://127.0.0.1:8000")
parser.add_argument("--log", required=True, help="server log file (to read the OTP code)")
parser.add_argument("--phone", default="09121234567")
args = parser.parse_args()
B = args.base.rstrip("/")
LOG = args.log
ok = lambda label, cond, extra="": print(("PASS " if cond else "FAIL ") + label + (f"  [{extra}]" if extra else "")) or cond
results = []

def check(label, cond, extra=""):
    results.append(ok(label, cond, extra))

# 1. Home screen, public
home = requests.get(f"{B}/api/v1/catalog/home/").json()
check("home: 3 top slides, category tiles with photos, ad slides, products",
      len(home["banners_top"]) == 3 and len(home["banners_middle"]) == 3 and len(home["categories"]) == 6
      and all(c["image"] for c in home["categories"]) and len(home["new_products"]) == 10,
      f"{len(home['banners_top'])} top, {len(home['banners_middle'])} ad slides, {len(home['categories'])} categories")
manto = next(c for c in home["categories"] if c["name"].endswith("مانتو"))
page = requests.get(f"{B}/api/v1/catalog/categories/{manto['slug']}/").json()
check("category page: 4 subcategories + slider", len(page["children"]) == 4 and len(page["banners"]) == 3,
      ", ".join(c["name"] for c in page["children"]))
office = next(c for c in page["children"] if "اداری" in c["name"])
office_products = requests.get(f"{B}/api/v1/catalog/products/", params={"category": office["slug"]}).json()["results"]
shop = office_products[0]["shop"]
shop_page = requests.get(f"{B}/api/v1/catalog/shops/{shop['slug']}/").json()
shop_items = requests.get(f"{B}/api/v1/catalog/products/", params={"shop": shop["slug"]}).json()["results"]
check("product opens its shop with the shop's other items", shop_page["product_count"] == len(shop_items) > 1,
      f"{shop_page['name']}: {len(shop_items)} items")
wait = requests.get(f"{B}/api/v1/catalog/banners/", params={"position": "tryon_wait"}).json()
check("try-on waiting ads", len(wait) == 3)
check("image URLs are absolute and load", requests.get(home["banners_top"][0]["image"]).status_code == 200)

# 2. Guest session
guest = requests.post(f"{B}/api/v1/auth/guest/").json()
H = {"Authorization": f"Bearer {guest['access']}"}
check("guest login", guest["user"]["is_guest"] is True)

# 3. Upload a photo (portrait, textured)
img = Image.new("RGB", (768, 1024), (180, 140, 120))
d = ImageDraw.Draw(img)
for y in range(0, 1024, 32):
    for x in range(0, 768, 32):
        if (x // 32 + y // 32) % 2 == 0:
            d.rectangle([x, y, x + 31, y + 31], fill=(125, 85, 65))
buf = io.BytesIO(); img.save(buf, "JPEG")
photo = requests.post(f"{B}/api/v1/tryon/photos/", headers=H, files={"image": ("me.jpg", buf.getvalue(), "image/jpeg")})
check("photo upload accepted", photo.status_code == 201, photo.status_code)
photo_id = photo.json()["id"]

dark = io.BytesIO(); Image.new("RGB", (768, 1024), (8, 8, 8)).save(dark, "JPEG")
rej = requests.post(f"{B}/api/v1/tryon/photos/", headers=H, files={"image": ("d.jpg", dark.getvalue(), "image/jpeg")})
check("dark photo rejected with Persian reason", rej.status_code == 400 and "تاریک" in rej.json()["detail"], rej.json()["detail"])

# 4. Try-on: pick a try-on product from home
product = home["tryon_products"][0]
job = requests.post(f"{B}/api/v1/tryon/jobs/", headers=H, json={"product_id": product["id"], "photo_id": photo_id})
check("try-on accepted (202)", job.status_code == 202, job.json().get("status"))
job_id = job.json()["id"]
for _ in range(20):
    polled = requests.get(f"{B}/api/v1/tryon/jobs/{job_id}/", headers=H).json()
    if polled["status"] in ("completed", "failed"):
        break
    time.sleep(0.5)
check("try-on completed", polled["status"] == "completed", f"{polled['status_label']}, {polled['generation_seconds']}s")
check("result image downloads", requests.get(polled["result_image"]).headers.get("Content-Type", "").startswith("image/"))

again = requests.post(f"{B}/api/v1/tryon/jobs/", headers=H, json={"product_id": product["id"], "photo_id": photo_id})
check("repeat served instantly from cache (200)", again.status_code == 200 and again.json()["from_cache"])
quota = requests.get(f"{B}/api/v1/tryon/quota/", headers=H).json()
check("guest quota counts only the real GPU call", quota == {"limit": 3, "used": 1, "remaining": 2}, quota)

shoes = next(p for p in requests.get(f"{B}/api/v1/catalog/products/", params={"search": "کتانی"}).json()["results"])
sj = requests.post(f"{B}/api/v1/tryon/jobs/", headers=H, json={"product_id": shoes["id"], "photo_id": photo_id})
check("shoes refused (not yet supported)", sj.status_code == 400, sj.json().get("code"))

# 5. Guest cart, then checkout requires login
variant = requests.get(f"{B}/api/v1/catalog/products/{product['slug']}/").json()["variants"][1]
cart = requests.post(f"{B}/api/v1/orders/cart/items/", headers=H, json={"variant_id": variant["id"], "quantity": 2}).json()
check("guest cart", cart["total"] == 2 * variant["price"], cart["total"])

# 6. OTP login using the same guest token -> account upgraded, data kept
r = requests.post(f"{B}/api/v1/auth/otp/request/", json={"phone": args.phone})
check("OTP requested", r.status_code == 200, r.json()["detail"])
time.sleep(0.5)
code = re.findall(rf"OTP for {args.phone}: (\d+)", open(LOG, encoding="utf-8").read())[-1]
login = requests.post(f"{B}/api/v1/auth/otp/verify/", headers=H, json={"phone": args.phone, "code": code}).json()
check("OTP verified, guest upgraded in place", login["user"]["id"] == guest["user"]["id"] and not login["user"]["is_guest"])
H = {"Authorization": f"Bearer {login['access']}"}
check("try-on history kept after login", requests.get(f"{B}/api/v1/tryon/jobs/", headers=H).json()["count"] == 2)
check("cart kept after login", len(requests.get(f"{B}/api/v1/orders/cart/", headers=H).json()["items"]) == 1)

# 7. Address + checkout + sandbox payment
addr = requests.post(f"{B}/api/v1/orders/addresses/", headers=H, json={
    "recipient_name": "سارا محمدی", "recipient_phone": "۰۹۱۲۱۲۳۴۵۶۷", "province": "تهران", "city": "تهران",
    "address": "خیابان ولیعصر", "postal_code": "۱۲۳۴۵-۶۷۸۹۰"}).json()
check("address saved (Persian digits normalized)", addr.get("postal_code") == "1234567890", addr.get("postal_code"))
stock_before = variant["stock"]
order = requests.post(f"{B}/api/v1/orders/checkout/", headers=H, json={"address_id": addr["id"]}).json()
check("order created", order["status"] == "pending_payment", order["number"])
stock_after = requests.get(f"{B}/api/v1/catalog/products/{product['slug']}/").json()["variants"][1]["stock"]
check("stock reserved", stock_after == stock_before - 2, f"{stock_before} -> {stock_after}")
pay = requests.post(f"{B}/api/v1/orders/{order['number']}/pay/", headers=H).json()
bank = requests.get(pay["payment_url"])
check("sandbox bank page", bank.status_code == 200 and "درگاه آزمایشی" in bank.text)
success_link = re.search(r'href="([^"]+Status=OK)"', bank.text).group(1).replace("&amp;", "&")
back = requests.get(B + success_link, allow_redirects=False)
check("bank returns to the app via deep link", back.status_code == 302 and back.headers["Location"].startswith("sarkhiaboon://payment/result"), back.headers.get("Location"))
final = requests.get(f"{B}/api/v1/orders/{order['number']}/", headers=H).json()
check("order paid", final["status"] == "paid", final["status_label"])

# 8. Docs and admin
check("Swagger docs page", requests.get(f"{B}/api/docs/").status_code == 200)
check("admin login page", requests.get(f"{B}/admin/login/").status_code == 200)

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
