import django_filters
from django.db.models import Exists, OuterRef, Q

from apps.tryon.providers import available_tryon_types

from .models import Category, Product, ProductVariant


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(method="filter_category", label="نامک دسته‌بندی (شامل زیردسته‌ها)")
    shop = django_filters.CharFilter(field_name="shop__slug", label="نامک فروشگاه")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    size = django_filters.CharFilter(method="filter_size")
    color = django_filters.CharFilter(method="filter_color")
    tryon = django_filters.BooleanFilter(method="filter_tryon", label="فقط محصولات قابل پرو")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    discounted = django_filters.BooleanFilter(method="filter_discounted")

    class Meta:
        model = Product
        fields = ()

    def filter_category(self, queryset, name, value):
        category = Category.objects.filter(slug=value, is_active=True).first()
        if category is None:
            return queryset.none()
        return queryset.filter(category_id__in=category.descendant_ids())

    def _variant_exists(self, queryset, **lookups):
        variants = ProductVariant.objects.filter(product=OuterRef("pk"), is_active=True, **lookups)
        return queryset.filter(Exists(variants))

    def filter_size(self, queryset, name, value):
        return self._variant_exists(queryset, size__iexact=value)

    def filter_color(self, queryset, name, value):
        return self._variant_exists(queryset, color__iexact=value)

    def filter_in_stock(self, queryset, name, value):
        if value:
            return self._variant_exists(queryset, stock__gt=0)
        return queryset

    def filter_tryon(self, queryset, name, value):
        """Products a customer can actually try on with the active AI engine."""
        if not value:
            return queryset
        types = available_tryon_types()
        own_type = Q(tryon_type__in=types)
        inherited = Q(tryon_type="") & Q(category__tryon_type__in=types)
        return queryset.filter(tryon_enabled=True).filter(own_type | inherited)

    def filter_discounted(self, queryset, name, value):
        if value:
            return queryset.filter(compare_at_price__isnull=False)
        return queryset
