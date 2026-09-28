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
    heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 },
    children: [new TextRun({ text: t, font: FONT, bold: true, rightToLeft: true, color: NAVY })],
  });
}
function h2(t, color) {
  return new Paragraph({
    bidirectional: true, alignment: AlignmentType.START,
    heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 },
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
  styles: {
    default: {
      document: {
        run: { font: FONT, rightToLeft: true },
        paragraph: { bidirectional: true, alignment: AlignmentType.START },
      },
    },
  },
  numbering: {
    config: [{
      reference: "bl",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.START, style: { paragraph: { indent: { right: 720, hanging: 360 } } } }],
    }],
  },
  sections: [{
    properties: { page: { size: { width: 11907, height: 16840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children: [
      // ================= COVER =================
      gap(2200),
      new Paragraph({
        bidirectional: true, alignment: AlignmentType.START,
        children: [new TextRun({ text: "پروپوزال فنی", font: FONT, size: 28, bold: true, color: GREY, rightToLeft: true })],
      }),
      new Paragraph({
        bidirectional: true, alignment: AlignmentType.START, spacing: { before: 160, after: 160 },
        children: [new TextRun({ text: "معماری موتور هوش مصنوعی پرو مجازی", font: FONT, size: 46, bold: true, color: NAVY, rightToLeft: true })],
      }),
      new Paragraph({
        bidirectional: true, alignment: AlignmentType.START, spacing: { after: 1400 },
        children: [new TextRun({ text: "بررسی پیشنهاد معماری RunPod Serverless و مدل CatVTON برای اپلیکیشن سرخیابون، به‌همراه موارد نیازمند تصمیم و مسیرهای پیشنهادی اجرا", font: FONT, size: 24, color: "475569", rightToLeft: true })],
      }),
      divider(),
      meta("ارائه‌شده توسط: ", "داوود ایوازخانی — توسعه‌دهنده‌ی Django و Python"),
      meta("خطاب به: ", "جناب آقای ابراهیمی"),
      meta("تاریخ: ", "مهر ۱۴۰۵"),
      meta("وضعیت سند: ", "در انتظار تصمیم کارفرما"),
      new Paragraph({ children: [new PageBreak()] }),

      // ================= 1. SUMMARY =================
      h1("۱. خلاصه"),
      c("این سند، پاسخ فنی به پیشنهاد معماری ارسال‌شده از سوی کارفرما برای بخش پردازش هوش مصنوعی اپلیکیشن است. در این پیشنهاد، تولید تصویر پرو مجازی روی GPU ابری RunPod در حالت Serverless و با مدل متن‌باز CatVTON انجام می‌شود."),
      c("جمع‌بندی بررسی: معماری پیشنهادی درست و قابل اجراست و در چند نقطه از رویکرد قبلی بهتر است. با این حال، چهار موضوع باید پیش از تصمیم نهایی روشن شود، و این معماری نسبت به برآورد فعلی، کارهای جدیدی به دامنه‌ی پروژه اضافه می‌کند. در پایان سند، دو مسیر اجرا و سه سوال کلیدی آمده است که پاسخ آن‌ها مسیر نهایی را مشخص می‌کند."),

      // ================= 2. ARCHITECTURE =================
      h1("۲. معماری مورد توافق"),
      c("ساختار کلی جریان داده در سیستم، مطابق پیشنهاد کارفرما و به شرح زیر خواهد بود. این ساختار در هر دو مسیر اجرای بخش ۶ ثابت است؛ تنها جزء قابل تعویض آن، موتور تولید تصویر (مرحله‌ی ۵) است."),
      gap(80),
      table(
        ["شرح", "جزء", "مرحله"],
        [
          ["کاربر عکس خود و محصول موردنظر را انتخاب می‌کند", "اپلیکیشن موبایل", "۱"],
          ["دریافت درخواست، اعتبارسنجی تصویر و ثبت آن", "Backend / API", "۲"],
          ["ارسال عکس شخص، عکس محصول و نوع محصول (بالاتنه / پایین‌تنه / کفش)", "داده‌ی ارسالی", "۳"],
          ["نگهداری درخواست‌ها تا نوبت پردازش، برای جلوگیری از کندی و قطعی", "صف پردازش (Queue)", "۴"],
          ["اجرای مدل پرو مجازی و تولید تصویر نهایی", "موتور هوش مصنوعی روی GPU", "۵"],
          ["ذخیره‌ی تصویر خروجی و ارسال نشانی آن به اپلیکیشن", "ذخیره و بازگشت نتیجه", "۶"],
        ],
        [5000, 2600, 900], { boldCol: 1 }
      ),
      gap(160),
      c("در اپلیکیشن، وضعیت درخواست به‌صورت مرحله‌ای به کاربر نمایش داده می‌شود: در حال آماده‌سازی، در صف پردازش، در حال پرو، آماده شد."),
      note("اصل مهم: اپلیکیشن هرگز مستقیماً به GPU متصل نمی‌شود. تمام ارتباط از طریق Backend انجام می‌شود تا امنیت، کنترل هزینه و امکان تعویض موتور حفظ شود."),

      // ================= 3. STRENGTHS =================
      h1("۳. نقاط قوت پیشنهاد کارفرما"),
      lb("معماری لایه‌ای درست: ", "جریان داده به‌ترتیب از اپلیکیشن به بک‌اند، سپس به صف پردازش و در نهایت به GPU می‌رسد؛ این دقیقاً همان ساختاری است که در نقشه‌ی راه پروژه نیز در نظر گرفته شده بود."),
      lb("RunPod Serverless: ", "پیش‌تر مطرح شده بود که GPU اجاره‌ای در ترافیک کم به‌صرفه نیست، چون سرور بیکار هم هزینه دارد. حالت Serverless با قابلیت کاهش خودکار به صفر (scale-to-zero) و محاسبه‌ی ثانیه‌ای، دقیقاً همین مشکل را برطرف می‌کند."),
      lb("انتخاب CatVTON: ", "این مدل سبک است و حافظه‌ی GPU کمتری نیاز دارد، در نتیجه هزینه‌ی هر پردازش پایین‌تر می‌ماند."),
      lb("توجه به لایسنس IDM-VTON: ", "این مدل مجوز غیرتجاری دارد و استفاده از آن در یک محصول فروشگاهی می‌تواند ریسک حقوقی ایجاد کند. از این مدل در محصول نهایی استفاده نخواهد شد."),

      // ================= 4. OPEN ISSUES =================
      h1("۴. موارد نیازمند تصمیم پیش از اجرا"),
      h2("الف) نحوه‌ی پرداخت به RunPod — مهم‌ترین مورد", AMBER),
      c("RunPod برای شارژ حساب، کارت اعتباری بین‌المللی می‌خواهد. پیش از شروع، باید راهکار قطعی کارفرما برای شارژ ماهانه‌ی این حساب مشخص شود. اگر در میانه‌ی کار حساب شارژ نشود، سرویس پرو مجازی به‌طور کامل از کار می‌افتد و کاربران با خطا مواجه می‌شوند."),

      h2("ب) زمان راه‌اندازی اولیه (Cold Start)", AMBER),
      c("محاسبه‌ی هزینه‌ی هر تصویر در پیشنهاد کارفرما، تنها زمان پردازش خالص را در نظر گرفته است. در حالت Serverless، وقتی سرویس مدتی بیکار بوده و درخواست جدیدی می‌رسد، ابتدا باید کانتینر راه‌اندازی شود و مدل در حافظه‌ی GPU بارگذاری گردد. این مرحله برای مدل‌های دیفیوژن معمولاً چندین ده ثانیه طول می‌کشد و همین مدت نیز محاسبه می‌شود."),
      c("این موضوع دو اثر دارد:"),
      b("هزینه‌ی واقعی در ترافیک پراکنده، بیشتر از عدد محاسبه‌شده در پیشنهاد خواهد بود."),
      b("نخستین کاربر هر بازه، به‌جای چند ثانیه، ممکن است حدود یک دقیقه منتظر بماند که مستقیماً بر تجربه‌ی کاربری اثر می‌گذارد."),
      c("این موضوع قابل مدیریت است، اما باید از ابتدا در طراحی دیده شود."),

      h2("ج) پرو مجازی کفش", AMBER),
      c("همان‌طور که در پیشنهاد کارفرما نیز اشاره شده، مدل‌های پرو مجازی عمدتاً برای بالاتنه و پایین‌تنه طراحی شده‌اند. اگر کفش جزو محصولات نسخه‌ی اول است، به یک مسیر پردازش و مدل جداگانه نیاز است که باید مستقلاً بررسی و آزمایش شود."),

      h2("د) دسته‌بندی محصولات تحت پوشش", AMBER),
      c("در پیشنهاد، سه دسته‌ی بالاتنه، پایین‌تنه و کفش آمده است. هر دسته به آزمایش، تنظیم و گاه پیش‌پردازش جداگانه نیاز دارد. لازم است مشخص شود نسخه‌ی اول دقیقاً کدام دسته‌ها را پوشش می‌دهد."),

      // ================= 5. SCOPE =================
      h1("۵. اثر بر دامنه‌ی کار"),
      c("برآورد و زمان‌بندی توافق‌شده‌ی فعلی، بر مبنای «اتصال به یک سرویس آماده‌ی پرو مجازی» تنظیم شده بود. معماری جدید به این معناست که مدل هوش مصنوعی را خودمان روی GPU ابری میزبانی می‌کنیم. این تغییر، کارهای زیر را به پروژه اضافه می‌کند:"),
      gap(80),
      table(
        ["شرح", "کار اضافه"],
        [
          ["ساخت و تنظیم ایمیج Docker شامل PyTorch، CUDA و وابستگی‌های مدل", "آماده‌سازی محیط اجرا"],
          ["نصب، پیکربندی و آزمایش مدل CatVTON روی GPU", "استقرار مدل"],
          ["نوشتن handler و endpoint سمت GPU و اتصال آن به صف پردازش", "لایه‌ی ارتباط با GPU"],
          ["کاهش زمان راه‌اندازی اولیه و بهینه‌سازی زمان هر پردازش", "بهینه‌سازی Cold Start"],
          ["آزمایش کیفیت خروجی با عکس‌های واقعی برای هر دسته‌ی محصول", "آزمون کیفیت"],
          ["پایش، رفع خطا و به‌روزرسانی زیرساخت GPU پس از راه‌اندازی", "نگهداری زیرساخت"],
        ],
        [5600, 2900], { boldCol: 1 }
      ),
      gap(200),
      p([txt("طبیعتاً با افزوده شدن این آیتم‌ها به دامنه‌ی پروژه، هم مدت زمان اجرا و هم هزینه‌ها افزایش پیدا خواهد کرد. پس از روشن شدن تکلیف موارد بخش ۴، برآورد دقیق زمان و هزینه به کارفرما اعلام خواهد شد.", { bold: true, color: NAVY })]),

      // ================= 6. PATHS =================
      h1("۶. مسیرهای پیشنهادی اجرا"),
      h2("مسیر اول — شروع با سرویس آماده، مهاجرت بعدی", GREEN),
      c("نسخه‌ی اول با یک سرویس آماده‌ی پرو مجازی راه‌اندازی می‌شود، اما معماری دقیقاً مطابق طرح کارفرما ساخته می‌شود: Backend، صف پردازش، و یک لایه‌ی قابل تعویض برای موتور هوش مصنوعی. پس از راه‌اندازی و مشاهده‌ی حجم واقعی درخواست‌ها، مهاجرت به RunPod بدون بازنویسی پروژه انجام می‌شود."),
      b("اپلیکیشن سریع‌تر به دست کاربران می‌رسد."),
      b("تصمیم درباره‌ی GPU اختصاصی بر اساس آمار واقعی گرفته می‌شود، نه برآورد."),
      b("ریسک فنی راه‌اندازی مدل، از مسیر اصلی تحویل پروژه جدا می‌شود."),

      h2("مسیر دوم — استفاده از RunPod از همان ابتدا", GREEN),
      c("اگر کارفرما ترجیح می‌دهد از روز اول روی زیرساخت اختصاصی باشد، این مسیر نیز کاملاً شدنی است. در این حالت، مرحله‌ی آماده‌سازی مدل و Docker به زمان‌بندی اضافه می‌شود و در همان مرحله، کیفیت خروجی با عکس‌های واقعی محصولات کارفرما آزمایش خواهد شد."),
      b("از ابتدا کنترل کامل بر مدل و زیرساخت وجود دارد."),
      b("نیازی به مهاجرت بعدی نیست."),
      b("راهکار پرداخت به RunPod باید پیش از شروع قطعی شده باشد."),

      h2("مقایسه‌ی دو مسیر"),
      table(
        ["مسیر دوم — RunPod از ابتدا", "مسیر اول — سرویس آماده", "معیار"],
        [
          ["نیازمند زمان بیشتر برای آماده‌سازی مدل", "سریع‌تر", "زمان رسیدن به کاربر"],
          ["شامل کارهای اضافه‌ی بخش ۵", "مطابق دامنه‌ی فعلی", "دامنه‌ی نسخه‌ی اول"],
          ["از روز اول", "پس از مهاجرت", "کنترل بر مدل و زیرساخت"],
          ["پیش از شروع پروژه", "پس از مشاهده‌ی آمار واقعی", "زمان تصمیم درباره‌ی GPU"],
          ["باید از ابتدا حل شده باشد", "تا زمان مهاجرت فرصت هست", "مسئله‌ی پرداخت به RunPod"],
        ],
        [3000, 2800, 2700], { boldCol: 2 }
      ),
      gap(160),
      note("پیشنهاد مجری: مسیر اول. با این مسیر، نسخه‌ی اول سریع‌تر منتشر می‌شود و تصمیم درباره‌ی زیرساخت GPU با داده‌ی واقعی گرفته می‌شود. از آن‌جا که معماری از ابتدا مطابق طرح کارفرما و با موتور قابل تعویض ساخته می‌شود، هیچ‌یک از مزایای مسیر دوم از دست نمی‌رود."),

      // ================= 7. QUESTIONS =================
      h1("۷. سوالات نیازمند پاسخ کارفرما"),
      c("پاسخ به سه سوال زیر، مسیر نهایی پروژه را مشخص می‌کند:"),
      table(
        ["پاسخ کارفرما", "سوال", "ردیف"],
        [
          ["", "راهکار پرداخت و شارژ ماهانه‌ی حساب RunPod چیست؟", "۱"],
          ["", "آیا پرو مجازی کفش در نسخه‌ی اول وجود دارد، یا فعلاً فقط لباس؟", "۲"],
          ["", "کدام مسیر اجرا (اول یا دوم) ترجیح داده می‌شود؟", "۳"],
        ],
        [3300, 4400, 800]
      ),

      // ================= 8. NEXT =================
      h1("۸. مراحل بعدی"),
      b("دریافت پاسخ کارفرما به سه سوال بخش ۷"),
      b("به‌روزرسانی نقشه‌ی راه پروژه بر اساس مسیر انتخاب‌شده"),
      b("اعلام برآورد نهایی زمان و هزینه"),
      b("نهایی‌سازی قرارداد و شروع اجرا"),
      p([txt("برای هرگونه پرسش یا بررسی جزئیات فنی، در خدمت هستم.")], { spacing: { before: 120 } }),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("gpu_proposal.docx", buf);
  console.log("done, bytes:", buf.length);
});
