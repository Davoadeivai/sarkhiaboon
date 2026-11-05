"""
The client's catalog spreadsheet: one definition shared by
    python manage.py catalog_template <out.xlsx>                 (blank template to send to the client)
    python manage.py import_catalog <filled.xlsx> --images <dir> (load the filled template into the store)

Layout of every data sheet (right-to-left):
    row 1  instructions for that sheet
    row 2  column headers (* = required)
    row 3  grey example row — never imported
    row 4+ the client's data (yellow cells); the last column checks each row with a formula
"""
from dataclasses import dataclass, field

EXAMPLE_ROW = 3
FIRST_DATA_ROW = 4
LAST_ROW = 400

TRYON_CHOICES = {
    "بالاتنه": "upper_body",
    "پایین‌تنه": "lower_body",
    "لباس یک‌تکه": "dresses",
    "کفش": "shoes",
    "بدون پرو": "none",
}
YES_NO = {"بله": True, "خیر": False}
BANNER_POSITIONS = {
    "بالای صفحه‌ی اصلی": "home_top",
    "تبلیغ میانه‌ی صفحه‌ی اصلی": "home_middle",
    "بالای صفحه‌ی دسته": "category_top",
    "هنگام ساخت تصویر پرو": "tryon_wait",
}
LINK_TYPES = {"بدون لینک": "none", "دسته": "category", "محصول": "product", "نشانی اینترنتی": "url"}


@dataclass
class Column:
    key: str
    title: str
    required: bool = False
    width: int = 18
    choices: list | None = None  # inline dropdown
    source: str | None = None  # dropdown from another sheet's first column
    number: bool = False
    note: str = ""


@dataclass
class Sheet:
    name: str
    help: str
    columns: list
    example: list
    prefill: list = field(default_factory=list)
    check: str = ""  # formula template for the status column; {r} = row number


SHOPS = Sheet(
    "فروشگاه‌ها",
    "هر ردیف یک فروشگاه ثبت‌شده. نام فایل‌ها همان نام فایل عکس در پوشه‌ی تصاویر است (مثلاً lale-logo.png).",
    [
        Column("name", "نام فروشگاه", True, 24),
        Column("city", "شهر", width=14),
        Column("description", "معرفی کوتاه (یک جمله)", width=40),
        Column("logo", "فایل لوگو (مربع)", width=22, note="PNG یا JPG مربع، حداقل ۲۵۶×۲۵۶ پیکسل"),
        Column("cover", "فایل تصویر سربرگ (افقی)", width=24, note="افقی، حدود ۱۲۰۰×۴۸۰ پیکسل"),
    ],
    ["بوتیک لاله", "تهران", "مانتو و پوشاک روزمره، دوخت تهران.", "lale-logo.png", "lale-cover.jpg"],
    check='=IF(COUNTA(A{r}:E{r})=0,"",IF(A{r}="","ناقص: نام فروشگاه",IF(COUNTIF($A${first}:$A${last},A{r})>1,"نام تکراری","کامل")))',
)

CATEGORIES = Sheet(
    "دسته‌ها",
    "دسته‌های پیشنهادی از قبل نوشته شده‌اند؛ تأیید، ویرایش یا اضافه کنید. برای زیردسته، «دسته‌ی والد» را انتخاب کنید.",
    [
        Column("name", "نام دسته", True, 22),
        Column("parent", "دسته‌ی والد (برای زیردسته)", width=24, source="دسته‌ها"),
        Column("tryon", "نوع پرو مجازی", True, 16, choices=list(TRYON_CHOICES)),
        Column("home", "نمایش در صفحه‌ی اصلی", width=18, choices=list(YES_NO)),
        Column("image", "فایل عکس کاشی دسته", width=24, note="عمودی، حدود ۳۶۰×۴۴۰ پیکسل"),
        Column("order", "ترتیب نمایش", width=12, number=True),
    ],
    ["مانتو", "", "لباس یک‌تکه", "بله", "manto.jpg", 1],
    prefill=[
        ["مانتو", "", "لباس یک‌تکه", "بله", "", 1],
        ["مانتو مدرسه", "مانتو", "لباس یک‌تکه", "خیر", "", 1],
        ["مانتو اداری", "مانتو", "لباس یک‌تکه", "خیر", "", 2],
        ["مانتو مجلسی", "مانتو", "لباس یک‌تکه", "خیر", "", 3],
        ["مانتو راحتی", "مانتو", "لباس یک‌تکه", "خیر", "", 4],
        ["شومیز و بلوز", "", "بالاتنه", "بله", "", 2],
        ["تیشرت", "", "بالاتنه", "بله", "", 3],
        ["شلوار", "", "پایین‌تنه", "بله", "", 4],
        ["کفش", "", "کفش", "بله", "", 5],
        ["کیف و اکسسوری", "", "بدون پرو", "بله", "", 6],
    ],
    check='=IF(COUNTA(A{r}:F{r})=0,"",IF(OR(A{r}="",C{r}=""),"ناقص: نام و نوع پرو",IF(COUNTIF($A${first}:$A${last},A{r})>1,"نام تکراری",IF(E{r}="","کامل (عکس کاشی ندارد)","کامل"))))',
)

PRODUCTS = Sheet(
    "محصولات",
    "هر ردیف یک محصول. «کد محصول» را خودتان بسازید (مثلاً M-101) و در برگه‌ی «سایز و موجودی» همان را بنویسید.",
    [
        Column("code", "کد محصول", True, 12),
        Column("name", "نام محصول", True, 28),
        Column("shop", "فروشگاه", True, 20, source="فروشگاه‌ها"),
        Column("category", "دسته", True, 20, source="دسته‌ها"),
        Column("price", "قیمت (تومان)", True, 16, number=True),
        Column("compare_at", "قیمت قبل از تخفیف (تومان)", width=20, number=True, note="فقط اگر تخفیف دارد؛ باید بیشتر از قیمت باشد"),
        Column("description", "توضیحات", width=40),
        Column("image", "فایل عکس اصلی", True, 20, note="عکس ویترین؛ می‌تواند روی مدل باشد"),
        Column("garment", "فایل عکس تمیز برای پرو", width=24, note="لباس به‌تنهایی، از روبه‌رو، زمینه‌ی ساده، بدون مدل و واترمارک، حداقل ۱۰۰۰ پیکسل"),
        Column("gallery", "فایل‌های عکس دیگر", width=26, note="چند نام فایل را با ویرگول جدا کنید"),
        Column("tryon", "پرو مجازی فعال", width=14, choices=list(YES_NO)),
    ],
    ["M-101", "مانتو اداری کرپ", "بوتیک لاله", "مانتو اداری", 1350000, 1550000,
     "کرپ نرم، جیب‌دار، مناسب محیط کار.", "M-101.jpg", "M-101-clean.jpg", "M-101-2.jpg, M-101-3.jpg", "بله"],
    check='=IF(COUNTA(A{r}:K{r})=0,"",IF(OR(A{r}="",B{r}="",C{r}="",D{r}="",E{r}="",H{r}=""),"ناقص: ستون‌های ستاره‌دار",'
          'IF(COUNTIF($A${first}:$A${last},A{r})>1,"کد تکراری",IF(AND(F{r}<>"",F{r}<=E{r}),"قیمت قبل از تخفیف باید بیشتر باشد",'
          'IF(I{r}="","کامل (بدون عکس پرو)","کامل")))))',
)

VARIANTS = Sheet(
    "سایز و موجودی",
    "برای هر سایز یا رنگِ هر محصول یک ردیف. اگر محصول سایز ندارد، یک ردیف با ستون سایز خالی کافی است.",
    [
        Column("code", "کد محصول", True, 14, source="محصولات"),
        Column("size", "سایز", width=10),
        Column("color", "رنگ", width=14),
        Column("color_hex", "کد رنگ (اختیاری)", width=16, note="مثلاً #1F3864"),
        Column("stock", "موجودی", True, 10, number=True),
        Column("price", "قیمت متفاوت (تومان)", width=18, number=True, note="فقط اگر این سایز قیمت دیگری دارد"),
    ],
    ["M-101", "M", "مشکی", "#1C1A2B", 8, ""],
    check='=IF(COUNTA(A{r}:F{r})=0,"",IF(OR(A{r}="",E{r}=""),"ناقص: کد و موجودی",'
          "IF(COUNTIF('محصولات'!$A${first}:$A${last},A{r})=0,\"این کد در برگه‌ی محصولات نیست\",\"کامل\")))",
)

BANNERS = Sheet(
    "بنرها",
    "تصویر بنر با نسبت ۲ به ۱ (مثلاً ۱۲۰۰×۶۰۰). برای «بالای صفحه‌ی دسته»، دسته را انتخاب کنید. تاریخ‌ها شمسی، مثل ۱۴۰۵/۰۹/۰۱.",
    [
        Column("position", "جایگاه", True, 24, choices=list(BANNER_POSITIONS)),
        Column("page", "دسته‌ی محل نمایش", width=20, source="دسته‌ها"),
        Column("title", "عنوان (برای مدیریت)", True, 24),
        Column("image", "فایل تصویر", True, 20),
        Column("link_type", "لینک به", width=16, choices=list(LINK_TYPES)),
        Column("link", "مقصد لینک", width=26, note="نام دسته، کد محصول، یا نشانی کامل اینترنتی"),
        Column("starts", "تاریخ شروع (شمسی)", width=16),
        Column("ends", "تاریخ پایان (شمسی)", width=16),
        Column("order", "ترتیب", width=8, number=True),
    ],
    ["بالای صفحه‌ی اصلی", "", "حراج پاییزه", "banner-autumn.jpg", "دسته", "مانتو", "1405/09/01", "1405/09/30", 1],
    check='=IF(COUNTA(A{r}:I{r})=0,"",IF(OR(A{r}="",C{r}="",D{r}=""),"ناقص: ستون‌های ستاره‌دار",'
          'IF(AND(A{r}="بالای صفحه‌ی دسته",B{r}=""),"دسته‌ی محل نمایش را انتخاب کنید",'
          'IF(AND(E{r}<>"",E{r}<>"بدون لینک",F{r}=""),"مقصد لینک خالی است","کامل"))))',
)

SHEETS = [SHOPS, CATEGORIES, PRODUCTS, VARIANTS, BANNERS]


# ---------------------------------------------------------------- dates

def jalali_to_gregorian(jy: int, jm: int, jd: int):
    """Convert a Jalali (Solar Hijri) date to a Gregorian (year, month, day)."""
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd
    days += (jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    month_days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > month_days[gm]:
        gd -= month_days[gm]
        gm += 1
    return gy, gm, gd


# ---------------------------------------------------------------- template

def build_template(path):
    """Write the blank spreadsheet the client fills in."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    FONT = "Tahoma"
    ink, mute = "1C1A2B", "6E6B80"
    head_fill = PatternFill("solid", fgColor="B3261E")  # the app's entry red
    input_fill = PatternFill("solid", fgColor="FFF8DC")  # cells the client fills
    example_fill = PatternFill("solid", fgColor="EDEEF2")
    thin = Side(style="thin", color="DFE1E8")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    right = Alignment(horizontal="right", vertical="center", wrap_text=True, readingOrder=2)

    wb = Workbook()
    guide = wb.active
    guide.title = "راهنما"
    guide.sheet_view.rightToLeft = True
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 90
    lines = [
        ("قالب اطلاعات فروشگاه سرخیابون", ""),
        ("", ""),
        ("چطور پر کنیم", "در هر برگه، از ردیف ۴ به بعد بنویسید (خانه‌های زرد). ردیف ۳ خاکستری فقط نمونه است و وارد سایت نمی‌شود."),
        ("ستون‌های ستاره‌دار (*)", "الزامی‌اند. ستون آخر هر برگه («وضعیت») خودکار می‌گوید هر ردیف کامل است یا چه چیزی کم دارد."),
        ("فهرست‌های کشویی", "برای فروشگاه، دسته، نوع پرو و جایگاه بنر، از فهرست کشویی انتخاب کنید تا املا یکی بماند."),
        ("ترتیب پر کردن", "۱) فروشگاه‌ها  ۲) دسته‌ها  ۳) محصولات  ۴) سایز و موجودی  ۵) بنرها"),
        ("عکس‌ها", "همه‌ی عکس‌ها را در یک پوشه بگذارید و نام هر فایل را دقیقاً در ستون مربوط بنویسید (مثلاً M-101.jpg). "
                   "نام فایل‌ها لاتین و بدون فاصله باشد."),
        ("عکس تمیز برای پرو", "مهم‌ترین عکس: لباس به‌تنهایی، از روبه‌رو و کامل در کادر، روی زمینه‌ی ساده‌ی سفید یا طوسی، بدون مدل و واترمارک، "
                              "حداقل ۱۰۰۰ پیکسل. کیفیت پرو مجازی مستقیم به این عکس بستگی دارد."),
        ("قیمت‌ها", "به تومان و بدون ویرگول یا حروف (مثلاً 1350000)."),
        ("تاریخ‌ها", "شمسی، به شکل 1405/09/01."),
        ("تحویل", "این فایل و پوشه‌ی عکس‌ها را با هم بفرستید. با یک دستور، همه‌چیز یک‌جا وارد سایت می‌شود."),
    ]
    for i, (a, b) in enumerate(lines, start=1):
        guide.cell(i, 1, a).font = Font(name=FONT, bold=True, size=16 if i == 1 else 11, color="B3261E" if i == 1 else ink)
        guide.cell(i, 2, b).font = Font(name=FONT, size=11, color=ink)
        for c in (1, 2):
            guide.cell(i, c).alignment = right
        if b:
            guide.row_dimensions[i].height = 34
    legend_row = len(lines) + 2
    guide.cell(legend_row, 1, "راهنمای رنگ‌ها").font = Font(name=FONT, bold=True, color=ink)
    for k, (fill, text) in enumerate([(input_fill, "خانه‌ای که شما پر می‌کنید"), (example_fill, "ردیف نمونه (وارد نمی‌شود)"),
                                      (head_fill, "عنوان ستون")]):
        cell = guide.cell(legend_row + 1 + k, 1, "")
        cell.fill = fill
        guide.cell(legend_row + 1 + k, 2, text).font = Font(name=FONT, color=ink)
        guide.cell(legend_row + 1 + k, 2).alignment = right

    for spec in SHEETS:
        ws = wb.create_sheet(spec.name)
        ws.sheet_view.rightToLeft = True
        ncols = len(spec.columns) + 1  # + status column
        status_col = ncols
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
        ws.cell(1, 1, spec.help).font = Font(name=FONT, size=10, color=mute)
        ws.cell(1, 1).alignment = right
        ws.row_dimensions[1].height = 34
        for c, col in enumerate(spec.columns, start=1):
            letter = get_column_letter(c)
            ws.column_dimensions[letter].width = col.width
            h = ws.cell(2, c, col.title + (" *" if col.required else ""))
            h.font = Font(name=FONT, bold=True, color="FFFFFF")
            h.fill = head_fill
            h.alignment = right
            h.border = box
            if col.note:
                h.comment = Comment(col.note, "سرخیابون")
            ex = ws.cell(EXAMPLE_ROW, c, spec.example[c - 1] if spec.example[c - 1] != "" else None)
            ex.font = Font(name=FONT, italic=True, color=mute)
            ex.fill = example_fill
            ex.alignment = right
            ex.border = box
            for r in range(FIRST_DATA_ROW, FIRST_DATA_ROW + 150):
                cell = ws.cell(r, c)
                cell.fill = input_fill
                cell.border = box
                cell.font = Font(name=FONT, color=ink)
                cell.alignment = right
                if col.number:
                    cell.number_format = "#,##0"
            rng = f"{letter}{FIRST_DATA_ROW}:{letter}{LAST_ROW}"
            if col.choices:
                dv = DataValidation(type="list", formula1='"' + ",".join(col.choices) + '"', allow_blank=True)
                dv.error, dv.errorTitle = "از فهرست انتخاب کنید.", "مقدار نامعتبر"
                ws.add_data_validation(dv)
                dv.add(rng)
            elif col.source:
                dv = DataValidation(type="list", formula1=f"='{col.source}'!$A${FIRST_DATA_ROW}:$A${LAST_ROW}", allow_blank=True)
                dv.error, dv.errorTitle = f"از فهرست برگه‌ی «{col.source}» انتخاب کنید.", "مقدار نامعتبر"
                ws.add_data_validation(dv)
                dv.add(rng)
            elif col.number:
                dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
                dv.error, dv.errorTitle = "فقط عدد بنویسید (بدون ویرگول و حروف).", "عدد لازم است"
                ws.add_data_validation(dv)
                dv.add(rng)
        for r, row in enumerate(spec.prefill, start=FIRST_DATA_ROW):
            for c, value in enumerate(row, start=1):
                if value != "":
                    ws.cell(r, c, value)
        st = get_column_letter(status_col)
        ws.column_dimensions[st].width = 30
        head = ws.cell(2, status_col, "وضعیت (خودکار)")
        head.font, head.fill, head.alignment, head.border = Font(name=FONT, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1C1A2B"), right, box
        for r in range(FIRST_DATA_ROW, FIRST_DATA_ROW + 150):
            cell = ws.cell(r, status_col, spec.check.format(r=r, first=FIRST_DATA_ROW, last=LAST_ROW))
            cell.font = Font(name=FONT, color=mute, size=9)
            cell.alignment = right
            cell.border = box
        ws.freeze_panes = ws.cell(FIRST_DATA_ROW, 1)
    for ws in wb.worksheets:  # print: landscape, one page wide
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    wb.active = 0
    wb.save(path)
