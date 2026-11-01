const PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹';

/** 123 → ۱۲۳ */
export function faDigits(input: string | number): string {
  return String(input).replace(/[0-9]/g, (d) => PERSIAN_DIGITS[Number(d)]);
}

/** ۱۲۳ / ١٢٣ → 123 (for inputs the user types with a Persian keyboard). */
export function enDigits(input: string): string {
  return input
    .replace(/[۰-۹]/g, (d) => String(PERSIAN_DIGITS.indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d)));
}

/** 1490000 → ۱٬۴۹۰٬۰۰۰ */
export function faNumber(n: number): string {
  const grouped = Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '٬');
  return faDigits(grouped);
}

/** 1490000 → ۱٬۴۹۰٬۰۰۰ تومان */
export function toman(n: number): string {
  return `${faNumber(n)} تومان`;
}

const ORDINALS = ['اول', 'دوم', 'سوم', 'چهارم', 'پنجم', 'ششم', 'هفتم', 'هشتم', 'نهم', 'دهم'];

/** 2 → «نفر دوم» style ordinal used for queue position. */
export function faOrdinal(n: number): string {
  return ORDINALS[n - 1] ?? `${faDigits(n)}ام`;
}

/** ISO date → «۱۲ آبان ۱۴۰۵» using the device's Persian calendar support. */
export function faDate(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return faDigits(iso.slice(0, 10));
  }
}

/** Keep a run of digits/codes in left-to-right order inside Persian text (Unicode isolate). */
export const ltr = (s: string) => `\u2066${s}\u2069`;

/** ۰۹۱۲ ۳۴۵ ۶۷۸۹ — grouped, and isolated so the groups don't reverse in RTL text. */
export function faPhone(phone: string | null | undefined): string {
  if (!phone) return '';
  const p = phone.replace(/\D/g, '');
  return ltr(faDigits(p.length === 11 ? `${p.slice(0, 4)} ${p.slice(4, 7)} ${p.slice(7)}` : p));
}
