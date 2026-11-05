from django.db.models import Count, Prefetch, Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, mixins, permissions, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.authentication import OptionalJWTAuthentication

from .filters import ProductFilter
from .models import Banner, Category, Favorite, HomeShortcut, Product, ProductVariant, Shop
from .serializers import (
    BannerSerializer,
    CategoryPageSerializer,
    CategorySerializer,
    FavoriteSerializer,
    HomeShortcutSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ShopSerializer,
)


def _product_queryset():
    return (
        Product.objects.visible()
        .select_related("category", "shop")
        .prefetch_related(
            Prefetch("variants", queryset=ProductVariant.objects.order_by("pk")),
            "images",
        )
    )


class FavoriteContextMixin:
    """Adds the set of the user's favorite product ids so each product can show a heart icon."""

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["favorite_ids"] = set(user.favorites.values_list("product_id", flat=True))
        return context


class CategoryListView(generics.ListAPIView):
    """Category tree (top-level categories with nested children)."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related("children__children")


class CategoryPageView(generics.RetrieveAPIView):
    """
    One category page: subcategories (with tile images) and the slider banners for that page.
    The app shows subcategory tiles when there are children, otherwise the category's products.
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)
    serializer_class = CategoryPageSerializer
    lookup_field = "slug"
    lookup_value_regex = "[^/]+"

    def get_queryset(self):
        return Category.objects.filter(is_active=True).select_related("parent").prefetch_related("children")


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """Registered shops. A shop's products: GET /catalog/products/?shop=<slug>"""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)
    serializer_class = ShopSerializer
    lookup_field = "slug"
    lookup_value_regex = "[^/]+"

    def get_queryset(self):
        visible = Q(products__is_active=True)
        return Shop.objects.filter(is_active=True).annotate(product_count=Count("products", filter=visible))


class ProductViewSet(FavoriteContextMixin, viewsets.ReadOnlyModelViewSet):
    """
    Product listing and detail. Filters: category, min_price, max_price, size,
    color, tryon, in_stock, discounted.  Search: ?search=  Ordering: ?ordering=price|-price|-created_at
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)
    lookup_field = "slug"
    lookup_value_regex = "[^/]+"
    filterset_class = ProductFilter
    search_fields = ("name", "description", "category__name")
    ordering_fields = ("price", "created_at", "name")
    ordering = ("-created_at",)

    def get_queryset(self):
        return _product_queryset()

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer


class BannerListView(generics.ListAPIView):
    """Live banners. Optional ?position=home_top|home_middle"""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)
    serializer_class = BannerSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Banner.objects.live().select_related("product", "category")
        position = self.request.query_params.get("position")
        if position:
            qs = qs.filter(position=position)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(placement_category__slug=category)
        return qs


class HomeView(APIView):
    """Everything the home screen needs in a single request."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)

    def get_serializer_context(self):
        context = {"request": self.request}
        user = self.request.user
        if user.is_authenticated:
            context["favorite_ids"] = set(user.favorites.values_list("product_id", flat=True))
        return context

    @extend_schema(
        responses=inline_serializer(
            "HomeResponse",
            {
                "banners_top": BannerSerializer(many=True),
                "shortcuts": HomeShortcutSerializer(many=True),
                "categories": CategorySerializer(many=True),
                "banners_middle": BannerSerializer(many=True),
                "new_products": ProductListSerializer(many=True),
                "discounted_products": ProductListSerializer(many=True),
                "tryon_products": ProductListSerializer(many=True),
            },
        )
    )
    def get(self, request):
        ctx = self.get_serializer_context()
        banners = list(Banner.objects.live().select_related("product", "category"))
        products = _product_queryset()
        return Response(
            {
                "banners_top": BannerSerializer([b for b in banners if b.position == Banner.Position.HOME_TOP], many=True, context=ctx).data,
                "shortcuts": HomeShortcutSerializer(HomeShortcut.objects.live().select_related("product", "category"), many=True, context=ctx).data,
                "categories": CategorySerializer(
                    Category.objects.filter(is_active=True, show_on_home=True).prefetch_related("children"), many=True, context=ctx
                ).data,
                "banners_middle": BannerSerializer([b for b in banners if b.position == Banner.Position.HOME_MIDDLE], many=True, context=ctx).data,
                "new_products": ProductListSerializer(products.order_by("-created_at")[:10], many=True, context=ctx).data,
                "discounted_products": ProductListSerializer(
                    products.filter(compare_at_price__isnull=False).order_by("-created_at")[:10], many=True, context=ctx
                ).data,
                "tryon_products": ProductListSerializer(
                    ProductFilter({"tryon": True}, queryset=products).qs.order_by("-created_at")[:10], many=True, context=ctx
                ).data,
            }
        )


class FavoriteViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    GET  /favorites/                    list
    POST /favorites/  {product_id}      add (idempotent)
    DELETE /favorites/<product_id>/     remove
    """

    serializer_class = FavoriteSerializer
    lookup_field = "product_id"
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # API docs generation
            return Favorite.objects.none()
        return (
            Favorite.objects.filter(user=self.request.user, product__is_active=True)
            .select_related("product__category")
            .prefetch_related("product__variants")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context["favorite_ids"] = set(self.request.user.favorites.values_list("product_id", flat=True))
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=serializer.validated_data["product"])
        data = self.get_serializer(favorite).data
        return Response(data, status=201 if created else 200)

    @extend_schema(responses={204: None})
    def destroy(self, request, product_id=None):
        Favorite.objects.filter(user=request.user, product_id=product_id).delete()
        return Response(status=204)
