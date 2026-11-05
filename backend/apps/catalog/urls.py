from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import BannerListView, CategoryListView, CategoryPageView, FavoriteViewSet, HomeView, ProductViewSet, ShopViewSet

router = SimpleRouter()
router.register("products", ProductViewSet, basename="product")
router.register("shops", ShopViewSet, basename="shop")
router.register("favorites", FavoriteViewSet, basename="favorite")

urlpatterns = [
    path("home/", HomeView.as_view(), name="home"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<str:slug>/", CategoryPageView.as_view(), name="category-page"),
    path("banners/", BannerListView.as_view(), name="banner-list"),
] + router.urls
