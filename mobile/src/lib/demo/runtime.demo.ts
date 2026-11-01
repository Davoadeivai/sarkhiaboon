/**
 * Browser-only demo: answers every API call of the app with sample data, so the
 * real app runs as a single web page with no server. Used only when the app is
 * built with EXPO_PUBLIC_DEMO=1 (metro.config.js swaps it in for runtime.ts).
 *
 * The try-on is simulated: the garment drawing is placed onto the shopper's own
 * photo on a canvas, after a short queue → processing sequence. No AI runs here.
 */
import { DEMO_BANNERS, DEMO_CATEGORIES, DEMO_FONTS, DEMO_PERSON, DEMO_PRODUCTS, DEMO_SHORTCUTS } from './assets.generated';

// The demo page can open at any address; the app's router expects to start at "/".
if (typeof window !== 'undefined' && window.location.pathname !== '/') {
  try {
    window.history.replaceState(null, '', '/');
  } catch {
    /* ignore */
  }
}

type DemoApi = (path: string, method: string, body: unknown) => Promise<{ status: number; data: unknown }>;

export const DEMO = true;
export const demoFonts: Record<string, string> = DEMO_FONTS;
/** Illustrated full-length figure for visitors without their own photo. */
export const demoPerson: string = DEMO_PERSON;
export const DEMO_OTP = '12345';

const TRYON_TYPES = ['upper_body', 'lower_body', 'dresses'];
const DESCRIPTION =
  'پارچه‌ی نرم و خنک، مناسب استفاده‌ی روزانه. قبل از خرید، روی عکس خودت پرو کن تا ببینی رنگ و فرمش به تو می‌آید یا نه.';

/* ---------------- state ---------------- */

const now = () => new Date().toISOString();
let user = { id: 1, phone: null as string | null, first_name: '', last_name: '', is_guest: true, date_joined: now() };
const favorites = new Set<number>([3]);
const photos: { id: string; image: string; width: number; height: number; created_at: string; expires_at: string }[] = [];
type Job = {
  id: string;
  productId: number;
  photoId: string;
  createdAt: number;
  saved: boolean;
  fromCache: boolean;
  result: string | null;
  failed: boolean;
};
const jobs: Job[] = [];
let usedToday = 0;
let cart: { id: number; variantId: number; quantity: number }[] = [];
const addresses: Record<string, unknown>[] = [];
const orders: Record<string, unknown>[] = [];
let seq = 100;

/* ---------------- shaping helpers ---------------- */

const category = (id: number) => DEMO_CATEGORIES.find((c) => c.id === id)!;
const brief = (id: number) => {
  const c = category(id);
  return { id: c.id, name: c.name, slug: c.slug, icon: c.icon };
};
const supportsTryon = (p: (typeof DEMO_PRODUCTS)[number]) => TRYON_TYPES.includes(p.tryon_type);
const discount = (p: (typeof DEMO_PRODUCTS)[number]) =>
  p.compare_at_price ? Math.round((1 - p.price / p.compare_at_price) * 100) : 0;
const variants = (p: (typeof DEMO_PRODUCTS)[number]) =>
  (['S', 'M', 'L'] as const).map((size, i) => ({
    id: p.id * 10 + i,
    size,
    color: 'پیش‌فرض',
    color_hex: '',
    price: p.price,
    stock: [5, 8, 3][i],
    in_stock: true,
  }));
const findVariant = (vid: number) => {
  const p = DEMO_PRODUCTS.find((x) => x.id === Math.floor(vid / 10));
  const v = p && variants(p).find((x) => x.id === vid);
  return p && v ? { p, v } : null;
};

function listItem(p: (typeof DEMO_PRODUCTS)[number]) {
  return {
    id: p.id,
    name: p.name,
    slug: p.slug,
    image: p.image,
    price: p.price,
    compare_at_price: p.compare_at_price,
    discount_percent: discount(p),
    category: brief(p.category_id),
    supports_tryon: supportsTryon(p),
    in_stock: true,
    is_favorite: favorites.has(p.id),
  };
}

const quota = () => {
  const limit = user.is_guest ? 3 : 30;
  return { limit, used: usedToday, remaining: Math.max(0, limit - usedToday) };
};

function cartPayload() {
  const items = cart.map((it) => {
    const { p, v } = findVariant(it.variantId)!;
    return {
      id: it.id,
      quantity: it.quantity,
      line_total: v.price * it.quantity,
      variant: {
        id: v.id,
        product_id: p.id,
        product_name: p.name,
        product_slug: p.slug,
        image: p.image,
        size: v.size,
        color: v.color,
        price: v.price,
        stock: v.stock,
      },
    };
  });
  const subtotal = items.reduce((n, i) => n + i.line_total, 0);
  const shipping_cost = subtotal === 0 || subtotal >= 1_000_000 ? 0 : 60_000;
  return { items, subtotal, shipping_cost, total: subtotal + shipping_cost };
}

/* ---------------- simulated try-on ---------------- */

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new window.Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

/** Place the garment drawing on the shopper's photo (a stand-in for the AI engine). */
async function composite(personUri: string, product: (typeof DEMO_PRODUCTS)[number]): Promise<string> {
  const W = 768;
  const H = 1024;
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d')!;
  const person = await loadImage(personUri);
  const scale = Math.max(W / person.width, H / person.height); // cover
  const pw = person.width * scale;
  const ph = person.height * scale;
  ctx.drawImage(person, (W - pw) / 2, (H - ph) / 2, pw, ph);
  if (product.garment) {
    const g = await loadImage(product.garment);
    const box = {
      upper_body: { top: 0.2, width: 0.5 },
      lower_body: { top: 0.5, width: 0.38 },
      dresses: { top: 0.19, width: 0.54 },
    }[product.tryon_type as 'upper_body'] ?? { top: 0.2, width: 0.5 };
    const gw = W * box.width;
    const gh = (g.height / g.width) * gw;
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,0.18)';
    ctx.shadowBlur = 18;
    ctx.shadowOffsetY = 6;
    ctx.globalAlpha = 0.97;
    ctx.drawImage(g, (W - gw) / 2, H * box.top, gw, gh);
    ctx.restore();
  }
  return canvas.toDataURL('image/jpeg', 0.88);
}

function jobPayload(j: Job) {
  const p = DEMO_PRODUCTS.find((x) => x.id === j.productId)!;
  const age = (Date.now() - j.createdAt) / 1000;
  let status: 'queued' | 'processing' | 'completed' | 'failed';
  let queue_position: number | null = null;
  if (j.fromCache || j.result) status = 'completed';
  else if (j.failed) status = 'failed';
  else if (age < 2) {
    status = 'queued';
    queue_position = 2;
  } else if (age < 3.5) {
    status = 'queued';
    queue_position = 1;
  } else status = 'processing';

  if (status === 'processing' && age > 7 && !j.result) {
    const photo = photos.find((ph) => ph.id === j.photoId);
    if (photo) {
      composite(photo.image, p)
        .then((r) => {
          j.result = r;
        })
        .catch(() => {
          j.failed = true;
        });
    } else j.failed = true;
  }

  const labels = { queued: 'در صف', processing: 'در حال پردازش', completed: 'آماده', failed: 'ناموفق' };
  return {
    id: j.id,
    status,
    status_label: labels[status],
    queue_position,
    product: { id: p.id, name: p.name, slug: p.slug, image: p.image, price: p.price },
    tryon_type: p.tryon_type,
    result_image: status === 'completed' ? j.result : null,
    error_message: status === 'failed' ? 'ساخت تصویر انجام نشد. با یک عکس دیگر دوباره امتحان کن.' : '',
    generation_seconds: status === 'completed' && !j.fromCache ? 4 : null,
    from_cache: j.fromCache,
    is_saved: j.saved,
    created_at: new Date(j.createdAt).toISOString(),
    finished_at: status === 'completed' ? now() : null,
  };
}

/* ---------------- router ---------------- */

const ok = (data: unknown, status = 200) => ({ status, data });
const fail = (detail: string, status = 400, code?: string) => ({ status, data: { detail, code } });
const uid = () => Math.random().toString(16).slice(2) + Date.now().toString(16);

function parse(path: string) {
  const [p, q = ''] = path.split('?');
  const params = new URLSearchParams(q);
  return { segs: p.split('/').filter(Boolean), params };
}

function normalizePhone(raw: string) {
  const d = String(raw ?? '')
    .replace(/[۰-۹]/g, (c) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c)))
    .replace(/\D/g, '')
    .replace(/^98/, '0');
  const p = d.startsWith('9') ? `0${d}` : d;
  return /^09\d{9}$/.test(p) ? p : null;
}

export const demoApi: DemoApi = async (path, method, body) => {
  await new Promise((r) => setTimeout(r, 120)); // feel like a network
  const { segs, params } = parse(path);
  const b = (body ?? {}) as Record<string, any>;
  const [area, a, bSeg, c] = segs;

  /* auth */
  if (area === 'auth') {
    if (a === 'guest') return ok({ access: 'demo', refresh: 'demo', is_new_user: true, user }, 201);
    if (a === 'token') return ok({ access: 'demo' });
    if (a === 'otp' && bSeg === 'request') {
      if (!normalizePhone(b.phone)) return fail('شماره‌ی موبایل معتبر نیست. مثل ۰۹۱۲۱۲۳۴۵۶۷ وارد کن.');
      return ok({ detail: 'کد ورود ارسال شد.', expires_in: 120 });
    }
    if (a === 'otp' && bSeg === 'verify') {
      if (String(b.code) !== DEMO_OTP) return fail('کد واردشده درست نیست.');
      user = { ...user, phone: normalizePhone(b.phone), is_guest: false };
      return ok({ access: 'demo', refresh: 'demo', is_new_user: false, user });
    }
    if (a === 'me') {
      if (method === 'PATCH') user = { ...user, first_name: b.first_name ?? user.first_name, last_name: b.last_name ?? user.last_name };
      return ok(user);
    }
  }

  /* catalog */
  if (area === 'catalog') {
    if (a === 'home') {
      const all = DEMO_PRODUCTS.map(listItem);
      return ok({
        banners_top: DEMO_BANNERS.filter((x) => x.position === 'home_top'),
        shortcuts: DEMO_SHORTCUTS,
        categories: DEMO_CATEGORIES.map((x) => ({ ...x, children: [] })),
        banners_middle: DEMO_BANNERS.filter((x) => x.position === 'home_middle'),
        new_products: [...all].reverse(),
        discounted_products: all.filter((x) => x.compare_at_price),
        tryon_products: all.filter((x) => x.supports_tryon).reverse(),
      });
    }
    if (a === 'categories') return ok(DEMO_CATEGORIES.map((x) => ({ ...x, children: [] })));
    if (a === 'products' && bSeg) {
      const p = DEMO_PRODUCTS.find((x) => x.slug === decodeURIComponent(bSeg));
      if (!p) return fail('محصول پیدا نشد.', 404);
      return ok({ ...listItem(p), description: DESCRIPTION, images: [], variants: variants(p), tryon_type: p.tryon_type });
    }
    if (a === 'products') {
      let list = [...DEMO_PRODUCTS];
      const s = params.get('search');
      if (s) list = list.filter((p) => p.name.includes(s) || category(p.category_id).name.includes(s));
      const cat = params.get('category');
      if (cat) list = list.filter((p) => category(p.category_id).slug === cat);
      if (params.get('tryon') === 'true') list = list.filter(supportsTryon);
      if (params.get('discounted') === 'true') list = list.filter((p) => p.compare_at_price);
      const o = params.get('ordering');
      if (o === 'price') list.sort((x, y) => x.price - y.price);
      else if (o === '-price') list.sort((x, y) => y.price - x.price);
      else list.reverse();
      return ok({ count: list.length, next: null, previous: null, results: list.map(listItem) });
    }
    if (a === 'favorites') {
      if (method === 'POST') {
        favorites.add(Number(b.product_id));
        return ok({}, 201);
      }
      if (method === 'DELETE') {
        favorites.delete(Number(bSeg));
        return ok(undefined, 204);
      }
      const results = DEMO_PRODUCTS.filter((p) => favorites.has(p.id)).map((p) => ({ id: p.id, product: listItem(p) }));
      return ok({ count: results.length, next: null, previous: null, results });
    }
  }

  /* try-on */
  if (area === 'tryon') {
    if (a === 'quota') return ok(quota());
    if (a === 'photos') {
      if (method === 'POST') {
        const file = (body as FormData).get('image') as Blob;
        const img = await loadImage(URL.createObjectURL(file)).catch(() => null);
        if (!img) return fail('این فایل عکس نیست. یک عکس JPG یا PNG انتخاب کن.', 400, 'photo_rejected');
        if (img.height < img.width) return fail('عکس باید عمودی باشد؛ گوشی را عمودی نگه دار و تمام‌قد عکس بگیر.', 400, 'photo_rejected');
        const photo = {
          id: uid(),
          image: img.src,
          width: img.width,
          height: img.height,
          created_at: now(),
          expires_at: new Date(Date.now() + 86_400_000).toISOString(),
        };
        photos.unshift(photo);
        return ok(photo, 201);
      }
      return ok(photos);
    }
    if (a === 'jobs' && !bSeg) {
      if (method === 'POST') {
        const prior = jobs.find((j) => j.productId === Number(b.product_id) && j.photoId === b.photo_id && j.result);
        if (!prior && quota().remaining <= 0) return fail('سهمیه‌ی پروی امروزت تمام شد.', 429, 'quota_exceeded');
        const j: Job = {
          id: uid(),
          productId: Number(b.product_id),
          photoId: String(b.photo_id),
          createdAt: Date.now(),
          saved: false,
          fromCache: !!prior,
          result: prior?.result ?? null,
          failed: false,
        };
        if (!prior) usedToday += 1;
        jobs.unshift(j);
        return ok(jobPayload(j), prior ? 200 : 202);
      }
      const list = params.get('saved') === 'true' ? jobs.filter((j) => j.saved && j.result) : jobs;
      return ok({ count: list.length, next: null, previous: null, results: list.map(jobPayload) });
    }
    if (a === 'jobs' && bSeg) {
      const j = jobs.find((x) => x.id === bSeg);
      if (!j) return fail('این پرو پیدا نشد.', 404);
      if (c === 'save') {
        if (method === 'POST' && !j.result) return fail('فقط پروهای کامل‌شده قابل ذخیره هستند.');
        j.saved = method === 'POST';
      }
      return ok(jobPayload(j));
    }
  }

  /* cart, addresses, orders */
  if (area === 'orders') {
    if (a === 'cart' && !bSeg) return ok(cartPayload());
    if (a === 'cart' && bSeg === 'items') {
      if (method === 'POST') {
        const found = findVariant(Number(b.variant_id));
        if (!found) return fail('این کالا پیدا نشد.', 404);
        const existing = cart.find((x) => x.variantId === found.v.id);
        const qty = (existing?.quantity ?? 0) + Number(b.quantity ?? 1);
        if (qty > found.v.stock) return fail(`از این کالا فقط ${found.v.stock} عدد موجود است.`, 400, 'out_of_stock');
        if (existing) existing.quantity = qty;
        else cart.push({ id: ++seq, variantId: found.v.id, quantity: qty });
        return ok(cartPayload());
      }
      const item = cart.find((x) => x.id === Number(c));
      if (!item) return fail('این کالا در سبد نیست.', 404);
      if (method === 'DELETE') cart = cart.filter((x) => x !== item);
      if (method === 'PATCH') {
        const { v } = findVariant(item.variantId)!;
        if (Number(b.quantity) > v.stock) return fail(`از این کالا فقط ${v.stock} عدد موجود است.`, 400, 'out_of_stock');
        item.quantity = Number(b.quantity);
      }
      return ok(cartPayload());
    }
    if (a === 'addresses') {
      if (method === 'POST') {
        const fields: Record<string, string> = {};
        for (const k of ['recipient_name', 'province', 'city', 'address']) if (!String(b[k] ?? '').trim()) fields[k] = 'این فیلد را پر کن.';
        if (!normalizePhone(b.recipient_phone)) fields.recipient_phone = 'شماره‌ی موبایل معتبر نیست.';
        const postal = String(b.postal_code ?? '').replace(/[۰-۹]/g, (x) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(x))).replace(/[-\s]/g, '');
        if (!/^\d{10}$/.test(postal)) fields.postal_code = 'کد پستی باید ۱۰ رقم باشد.';
        if (Object.keys(fields).length) return { status: 400, data: Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, [v]])) };
        const addr = { ...b, id: ++seq, recipient_phone: normalizePhone(b.recipient_phone), postal_code: postal, is_default: true };
        addresses.push(addr);
        return ok(addr, 201);
      }
      return ok(addresses);
    }
    if (a === 'checkout') {
      if (user.is_guest) return fail('برای ثبت سفارش اول با شماره موبایل وارد شو.', 403, 'login_required');
      const addr = addresses.find((x) => x.id === Number(b.address_id));
      if (!addr) return fail('نشانی پیدا نشد.', 404, 'address_not_found');
      const cp = cartPayload();
      if (!cp.items.length) return fail('سبد خریدت خالی است.', 400, 'empty_cart');
      const order = {
        number: `SK${Math.floor(10_000_000 + Math.random() * 89_999_999)}`,
        status: 'pending_payment',
        status_label: 'در انتظار پرداخت',
        items: cp.items.map((i) => ({
          product_name: i.variant.product_name,
          variant_label: `${i.variant.size} / ${i.variant.color}`,
          unit_price: i.variant.price,
          quantity: i.quantity,
          line_total: i.line_total,
        })),
        subtotal: cp.subtotal,
        shipping_cost: cp.shipping_cost,
        total: cp.total,
        ...Object.fromEntries(['recipient_name', 'recipient_phone', 'province', 'city', 'address', 'postal_code'].map((k) => [k, addr[k]])),
        note: b.note ?? '',
        reserved_until: new Date(Date.now() + 30 * 60_000).toISOString(),
        paid_at: null as string | null,
        tracking_code: '',
        created_at: now(),
      };
      orders.unshift(order);
      cart = [];
      return ok(order, 201);
    }
    if (!a) return ok({ count: orders.length, next: null, previous: null, results: orders });
    const order = orders.find((o) => o.number === a);
    if (!order) return fail('سفارش پیدا نشد.', 404);
    if (bSeg === 'pay') {
      // No bank in the demo: the payment succeeds immediately.
      Object.assign(order, { status: 'paid', status_label: 'پرداخت‌شده', paid_at: now() });
      return ok({ payment_url: 'demo' });
    }
    if (bSeg === 'cancel') Object.assign(order, { status: 'cancelled', status_label: 'لغوشده' });
    return ok(order);
  }

  return fail('این بخش در نسخه‌ی نمایشی نیست.', 404);
};
