const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, LevelFormat, VerticalAlign
} = require("docx");

const FONT = "Vazirmatn";
const NAVY = "1F3864";
const GREY = "64748B";
const GREEN = "166534";
const AMBER = "92400E";

function txt(t, o = {}) {
  return new TextRun({
    text: t, font: FONT, size: o.size || 22, bold: o.bold || false,
    italics: o.italics || false, color: o.color, rightToLeft: true,
  });
}
function p(children, o = {}) {
  return new Paragraph({
    bidirectional: true,
    alignment: o.alignment || AlignmentType.JUSTIFIED,
    spacing: { after: 150, ...(o.spacing || {}) },
    children,
  });
}
function c(t) { return p([txt(t)]); }
function h1(t) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.START,
    heading: HeadingLevel.HEADING_1, keepNext: true, spacing: { before: 360, after: 160 },
    children: [new TextRun({ text: t, font: FONT, bold: true, rightToLeft: true, color: NAVY })],
  });
}
function h2(t, color) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.START,
    heading: HeadingLevel.HEADING_2, keepNext: true, spacing: { before: 240, after: 120 },
    children: [new TextRun({ text: t, font: FONT, bold: true, rightToLeft: true, color: color || "334155" })],
  });
}
function b(t, o = {}) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.START,
    numbering: { reference: "bl", level: 0 },
    spacing: { after: 100 }, children: [txt(t, o)],
  });
}
function lb(label, t) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.START,
    numbering: { reference: "bl", level: 0 },
    spacing: { after: 110 }, children: [txt(label, { bold: true }), txt(t)],
  });
}
function cell(t, o = {}) {
  return new TableCell({
    width: { size: o.width || 2000, type: WidthType.DXA },
    shading: o.shading ? { type: ShadingType.CLEAR, color: "auto", fill: o.shading } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 100, bottom: 100, left: 120, right: 120 },
    children: [new Paragraph({
      bidirectional: true, alignment: AlignmentType.START,
      children: [txt(t, { bold: o.bold, size: o.size || 20, color: o.color })],
    })],
  });
}
// columns are given left-to-right; the last one appears on the right
function table(headers, rows, widths, o = {}) {
  return new Table({
    width: { size: widths.reduce((a, x) => a + x, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, { bold: true, shading: NAVY, color: "FFFFFF", width: widths[i] })),
      }),
      ...rows.map((r, idx) => new TableRow({
        cantSplit: true,
        children: r.map((x, i) => cell(x, {
          width: widths[i],
          shading: idx % 2 === 0 ? "F1F5F9" : "FFFFFF",
          bold: o.boldCol !== undefined ? i === o.boldCol : false,
        })),
      })),
    ],
  });
}
function note(t) { return p([txt(t, { italics: true, color: GREY, size: 20 })]); }
function gap(n) { return new Paragraph({ spacing: { before: n || 160 }, children: [] }); }
function divider() {
  return new Paragraph({
    border: { bottom: { color: "CBD5E1", space: 1, style: BorderStyle.SINGLE, size: 6 } },
    spacing: { after: 240 }, children: [],
  });
}
function meta(label, value) {
  return p([txt(label, { bold: true }), txt(value)], { alignment: AlignmentType.START });
}

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, rightToLeft: true }, paragraph: { bidirectional: true, alignment: AlignmentType.START } } } },
  numbering: { config: [{ reference: "bl", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.START, style: { paragraph: { indent: { right: 720, hanging: 360 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11907, height: 16840 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    children: [
      new Paragraph({
        bidirectional: true, alignment: AlignmentType.START, spacing: { after: 80 },
        children: [new TextRun({ text: "سرخیابون", font: FONT, size: 40, bold: true, color: "B3261E", rightToLeft: true })],
      }),
      new Paragraph({
        bidirectional: true, alignment: AlignmentType.START, spacing: { after: 200 },
        children: [new TextRun({ text: "گزارش وضعیت پروژه و موارد لازم از طرف کارفرما", font: FONT, size: 26, bold: true, color: NAVY, rightToLeft: true })],
      }),
      meta("خطاب به: ", "جناب آقای ابراهیمی"),
      meta("از طرف: ", "داوود عیوض‌خانی — توسعه‌دهنده‌ی پروژه"),
      meta("تاریخ: ", "۱۴ آبان ۱۴۰۵"),
      divider(),

      c("سلام و وقت بخیر،"),
      c("گزارش کوتاهی از وضعیت فعلی پروژه‌ی سرخیابون و مواردی که برای ادامه‌ی کار از طرف شما لازم است، خدمتتان ارسال می‌کنم."),

      h2("آنچه تاکنون انجام شده: ساختار پروژه", NAVY),
      p([txt("تا این مرحله ", {}), txt("فقط ساختار پروژه ساخته شده است، نه کل پروژه.", { bold: true, color: "B3261E" }),
         txt(" یعنی اسکلت سرور، صفحه‌های اپلیکیشن و پنل مدیریت آماده است و با اطلاعات نمونه کار می‌کند، اما هنوز به نسخه‌ی نهایی و قابل انتشار نرسیده است. این ساختار شامل موارد زیر است:")]),
      b("ساختار سرور و پنل مدیریت (کاربران، محصولات، سبد خرید، سفارش و پرداخت)."),
      b("ساختار صفحه‌های اپلیکیشن، با چیدمانی که خواسته بودید: صفحه‌ی ورود قرمز، بنرهای اسلایدی، دسته‌ها و زیردسته‌های مانتو، صفحه‌ی فروشگاه و تبلیغ هنگام پرو."),
      b("نسخه‌ی نمایشی برای دیدن مسیر کلی کار؛ در این نسخه، پرو مجازی شبیه‌سازی شده است و نتیجه‌ی واقعی هوش مصنوعی نیست."),

      h2("آنچه هنوز باقی مانده است", NAVY),
      b("موتور هوش مصنوعی پرو مجازی؛ انتخاب مدل مناسب از نظر مجوز استفاده‌ی تجاری در حال بررسی است و جداگانه خدمتتان توضیح می‌دهم."),
      b("اتصال واقعی به درگاه پرداخت و سامانه‌ی پیامک، با حساب‌های شما."),
      b("وارد کردن اطلاعات و عکس‌های واقعی فروشگاه‌ها و محصولات."),
      b("تست روی گوشی‌های واقعی اندروید و آیفون، و رفع ایرادها."),
      b("راه‌اندازی روی سرور اصلی و انتشار در بازار و مایکت."),

      h2("موارد فوری از طرف شما", NAVY),
      c("برخی کارها زمان‌بر هستند و بهتر است از همین هفته شروع شوند:"),
      lb("اینماد: ", "پیش‌نیاز درگاه پرداخت است."),
      lb("درگاه زرین‌پال: ", "پس از دریافت اینماد."),
      lb("دامنه و سرور: ", "برای راه‌اندازی نسخه‌ی اصلی."),
      c("فهرست کامل ۱۷ مورد، با توضیح هر کدام، در فایل «فهرست آماده‌سازی کارفرما» آمده است."),

      h2("اطلاعات فروشگاه", NAVY),
      c("اطلاعات فروشگاه‌ها، دسته‌ها، محصولات، سایزها و بنرها را لطفاً در فایل اکسل پیوست وارد کنید و همراه پوشه‌ی عکس‌ها بفرستید. فایل فهرست کشویی دارد و ستون آخر هر برگه خودکار نشان می‌دهد هر ردیف کامل است یا چه چیزی کم دارد."),
      p([txt("نکته‌ی مهم: ", { bold: true }), txt("از هر لباس یک «عکس تمیز» لازم است؛ لباس به‌تنهایی، از روبه‌رو، روی زمینه‌ی ساده و بدون مدل. کیفیت پرو مجازی مستقیماً به همین عکس بستگی دارد.")]),

      h2("تصمیم‌های باقی‌مانده", NAVY),
      c("چند تصمیم در بخش ۵ فایل فهرست آماده‌سازی آمده است؛ از جمله مبلغ و شرایط پرداخت، و اینکه فروشگاه‌ها فقط از پنل مدیریت ثبت شوند یا پنل جداگانه برای فروشندگان هم لازم باشد. با افزوده شدن آیتم، هزینه‌ها هم افزایش پیدا خواهد کرد."),

      p([txt("برای هر پرسشی در خدمتم.")], { spacing: { before: 200 } }),
      p([txt("با احترام،")], { alignment: AlignmentType.START }),
      p([txt("داوود عیوض‌خانی", { bold: true })], { alignment: AlignmentType.START }),
      note("پیوست‌ها: فهرست آماده‌سازی کارفرما (PDF)، قالب اطلاعات فروشگاه سرخیابون (اکسل)"),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.argv[2] || "client_letter.docx";
  fs.writeFileSync(out, buf);
  console.log("done", out, buf.length);
});
