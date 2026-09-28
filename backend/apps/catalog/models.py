from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class TryOnType(models.TextChoices):
    """Which body region the try-on model should dress. Matches CatVTON's categories."""

    NONE = "none", "بدون پرو مجازی"
    UPPER_BODY = "upper_body", "بالاتنه"
    LOWER_BODY = "lower_body", "پایین‌تنه"
    DRESSES = "dresses", "لباس یک‌تکه"
    SHOES = "shoes", "کفش"


def unique_slug(instance, value, field="slug"):
    """Unicode-aware slug (Persian names stay readable) with a numeric suffix on collision."""
    base = slugify(value, allow_unicode=True)[:200] or "item"
    slug, n = base, 2
    model = type(instance)
    while model.objects.filter(**{field: slug}).exclude(pk=instance.pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(TimeStampedModel):
    name = models.CharField("نام", max_length=120)
    slug = models.SlugField("نامک", max_length=220, unique=True, allow_unicode=True, blank=True)
    parent = models.ForeignKey(
        "self", verbose_name="دسته‌ی والد", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    icon = models.ImageField("آیکون", upload_to="catalog/categories/", blank=True)
    tryon_type = models.CharField(
        "نوع پرو مجازی", max_length=20, choices=TryOnType.choices, default=TryOnType.NONE,
        help_text="محصولات این دسته به‌طور پیش‌فرض با این نوع پرو می‌شوند.",
    )
    show_on_home = models.BooleanField("نمایش در صفحه‌ی اصلی", default=False)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ("order", "name")

    def __str__(self):
        return f"{self.parent} › {self.name}" if self.parent_id else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def clean(self):
        # Prevent loops such as A -> B -> A
        node = self.parent
        while node is not None:
            if node.pk == self.pk:
                raise ValidationError({"parent": "دسته نمی‌تواند زیرمجموعه‌ی خودش باشد."})
            node = node.parent

    def descendant_ids(self):
        """This category and all nested children (used for filtering)."""
        ids, frontier = [self.pk], [self.pk]
        while frontier:
            frontier = list(Category.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            ids.extend(frontier)
        return ids


class ProductQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_active=True, category__is_active=True)


class Product(TimeStampedModel):
    name = models.CharField("نام", max_length=200)
    slug = models.SlugField("نامک", max_length=220, unique=True, allow_unicode=True, blank=True)
    category = models.ForeignKey(Category, verbose_name="دسته‌بندی", on_delete=models.PROTECT, related_name="products")
    description = models.TextField("توضیحات", blank=True)
    price = models.PositiveBigIntegerField("قیمت (تومان)")
    compare_at_price = models.PositiveBigIntegerField(
        "قیمت قبل از تخفیف (تومان)", null=True, blank=True,
        help_text="اگر پر شود، محصول تخفیف‌دار نمایش داده می‌شود.",
    )
    image = models.ImageField("تصویر اصلی", upload_to="catalog/products/")
    garment_image = models.ImageField(
        "تصویر لباس برای پرو مجازی", upload_to="catalog/garments/", blank=True,
        help_text="عکس تمیز خود لباس (بدون مدل، پس‌زمینه‌ی ساده). اگر خالی باشد، تصویر اصلی استفاده می‌شود.",
    )
    tryon_enabled = models.BooleanField("پرو مجازی فعال", default=True)
    tryon_type = models.CharField(
        "نوع پرو مجازی", max_length=20, choices=TryOnType.choices, blank=True,
        help_text="خالی بگذارید تا از دسته‌بندی گرفته شود.",
    )
    is_active = models.BooleanField("فعال", default=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("is_active", "-created_at"))]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def clean(self):
        if self.compare_at_price is not None and self.compare_at_price <= self.price:
            raise ValidationError({"compare_at_price": "قیمت قبل از تخفیف باید بیشتر از قیمت فعلی باشد."})

    @property
    def effective_tryon_type(self):
        return self.tryon_type or self.category.tryon_type

    @property
    def supports_tryon(self):
        return self.tryon_enabled and self.effective_tryon_type != TryOnType.NONE

    @property
    def tryon_garment_image(self):
        return self.garment_image or self.image

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return round(100 * (self.compare_at_price - self.price) / self.compare_at_price)
        return 0


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("تصویر", upload_to="catalog/products/gallery/")
    alt = models.CharField("متن جایگزین", max_length=200, blank=True)
    order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "تصویر گالری"
        verbose_name_plural = "گالری تصاویر"
        ordering = ("order", "pk")


class ProductVariant(models.Model):
    """A purchasable size/color combination with its own stock."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField("سایز", max_length=20, blank=True)
    color = models.CharField("رنگ", max_length=40, blank=True)
    color_hex = models.CharField("کد رنگ", max_length=7, blank=True, help_text="مثلاً #1F3864")
    sku = models.CharField("کد انبار (SKU)", max_length=60, unique=True, null=True, blank=True)
    stock = models.PositiveIntegerField("موجودی", default=0)
    price_override = models.PositiveBigIntegerField(
        "قیمت اختصاصی (تومان)", null=True, blank=True, help_text="خالی = همان قیمت محصول"
    )
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "تنوع (سایز/رنگ)"
        verbose_name_plural = "تنوع‌ها (سایز/رنگ)"
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(fields=("product", "size", "color"), name="unique_variant_per_product"),
        ]

    def __str__(self):
        parts = [p for p in (self.size, self.color) if p]
        return f"{self.product.name} — {' / '.join(parts) or 'تک‌سایز'}"

    @property
    def price(self):
        return self.price_override if self.price_override is not None else self.product.price


class LinkTargetMixin(models.Model):
    """Shared 'where does this tap go' fields for banners and home shortcuts."""

    class LinkType(models.TextChoices):
        NONE = "none", "بدون لینک"
        PRODUCT = "product", "محصول"
        CATEGORY = "category", "دسته‌بندی"
        URL = "url", "نشانی اینترنتی"

    link_type = models.CharField("نوع لینک", max_length=10, choices=LinkType.choices, default=LinkType.NONE)
    product = models.ForeignKey(Product, verbose_name="محصول", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    category = models.ForeignKey(Category, verbose_name="دسته‌بندی", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    url = models.URLField("نشانی", blank=True)

    class Meta:
        abstract = True

    def clean(self):
        required = {self.LinkType.PRODUCT: "product", self.LinkType.CATEGORY: "category", self.LinkType.URL: "url"}
        field = required.get(self.link_type)
        if field and not getattr(self, field):
            raise ValidationError({field: "برای این نوع لینک، این فیلد الزامی است."})


class ScheduledQuerySet(models.QuerySet):
    def live(self):
        now = timezone.now()
        return self.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gt=now),
        )


class Banner(LinkTargetMixin, TimeStampedModel):
    """Promotional banner shown in the app (requested by the client for the home screen)."""

    class Position(models.TextChoices):
        HOME_TOP = "home_top", "بالای صفحه‌ی اصلی (اسلایدر)"
        HOME_MIDDLE = "home_middle", "میانه‌ی صفحه‌ی اصلی"

    title = models.CharField("عنوان", max_length=150)
    image = models.ImageField("تصویر", upload_to="catalog/banners/")
    position = models.CharField("جایگاه", max_length=20, choices=Position.choices, default=Position.HOME_TOP)
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    starts_at = models.DateTimeField("شروع نمایش", null=True, blank=True)
    ends_at = models.DateTimeField("پایان نمایش", null=True, blank=True)

    objects = ScheduledQuerySet.as_manager()

    class Meta:
        verbose_name = "بنر"
        verbose_name_plural = "بنرها"
        ordering = ("position", "order", "-created_at")

    def __str__(self):
        return self.title


class HomeShortcut(LinkTargetMixin, TimeStampedModel):
    """Icon row on the home screen used for promotions (requested by the client)."""

    title = models.CharField("عنوان", max_length=60)
    icon = models.ImageField("آیکون", upload_to="catalog/shortcuts/")
    order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    starts_at = models.DateTimeField("شروع نمایش", null=True, blank=True)
    ends_at = models.DateTimeField("پایان نمایش", null=True, blank=True)

    objects = ScheduledQuerySet.as_manager()

    class Meta:
        verbose_name = "آیکون تبلیغاتی صفحه‌ی اصلی"
        verbose_name_plural = "آیکون‌های تبلیغاتی صفحه‌ی اصلی"
        ordering = ("order", "-created_at")

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("user", "product"), name="unique_favorite")]
