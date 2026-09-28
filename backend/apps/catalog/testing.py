"""Factories used by the test suites of catalog, tryon and orders."""
from apps.core.testing import make_image

from .models import Category, Product, ProductVariant, TryOnType


def make_category(name="تیشرت", tryon_type=TryOnType.UPPER_BODY, parent=None, **kwargs):
    return Category.objects.create(name=name, tryon_type=tryon_type, parent=parent, **kwargs)


def make_product(name="تیشرت نخی", category=None, price=450_000, stock=5, sizes=("M",), **kwargs):
    category = category or make_category()
    product = Product.objects.create(
        name=name, category=category, price=price, image=make_image("product.jpg", (600, 800)), **kwargs
    )
    for size in sizes:
        ProductVariant.objects.create(product=product, size=size, color="سفید", stock=stock)
    return product
