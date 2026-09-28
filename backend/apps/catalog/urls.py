from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import BannerListView, CategoryListView, FavoriteViewSet, HomeView, ProductViewSet

router = SimpleRouter()
router.register("products", ProductViewSet, basename="product")
router.register("favorites", FavoriteViewSet, basename="favorite")

urlpatterns = [
    path("home/", HomeView.as_view(), name="home"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("banners/", BannerListView.as_view(), name="banner-list"),
] + router.urls
