from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AddressViewSet,
    CartItemViewSet,
    CartView,
    CheckoutView,
    OrderViewSet,
    PaymentCallbackView,
    SandboxPaymentPage,
)

router = SimpleRouter()
router.register("cart/items", CartItemViewSet, basename="cart-item")
router.register("addresses", AddressViewSet, basename="address")

orders = SimpleRouter()
orders.register("", OrderViewSet, basename="order")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("payment/callback/", PaymentCallbackView.as_view(), name="payment-callback"),
    path("payment/sandbox/<str:authority>/", SandboxPaymentPage.as_view(), name="payment-sandbox"),
] + router.urls + orders.urls
