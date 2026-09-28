from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import escape
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .gateways import SandboxGateway, get_gateway
from .models import Address, CartItem, Order
from .serializers import (
    AddressSerializer,
    CartAddSerializer,
    CartItemSerializer,
    CartQuantitySerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderSerializer,
)


def _error(exc):
    return Response({"detail": str(exc), "code": exc.code}, status=exc.status)


def _cart_response(request):
    items, subtotal, shipping, total = services.cart_summary(request.user)
    return Response(CartSerializer(
        {"items": items, "subtotal": subtotal, "shipping_cost": shipping, "total": total},
        context={"request": request},
    ).data)


class CartView(APIView):
    """GET the cart with totals; DELETE empties it."""

    @extend_schema(responses=CartSerializer)
    def get(self, request):
        return _cart_response(request)

    @extend_schema(responses=CartSerializer)
    def delete(self, request):
        CartItem.objects.filter(user=request.user).delete()
        return _cart_response(request)


class CartItemViewSet(viewsets.GenericViewSet):
    """POST add a variant (adds to quantity if already in cart); PATCH set quantity; DELETE remove."""

    serializer_class = CartItemSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # API docs generation
            return CartItem.objects.none()
        return CartItem.objects.filter(user=self.request.user).select_related("variant__product__category")

    @extend_schema(request=CartAddSerializer, responses=CartSerializer)
    def create(self, request):
        payload = CartAddSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            services.add_to_cart(request.user, payload.validated_data["variant"], payload.validated_data["quantity"])
        except services.OrderError as exc:
            return _error(exc)
        return _cart_response(request)

    @extend_schema(request=CartQuantitySerializer, responses=CartSerializer)
    def partial_update(self, request, pk=None):
        payload = CartQuantitySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            services.set_cart_quantity(self.get_object(), payload.validated_data["quantity"])
        except services.OrderError as exc:
            return _error(exc)
        return _cart_response(request)

    @extend_schema(responses=CartSerializer)
    def destroy(self, request, pk=None):
        self.get_object().delete()
        return _cart_response(request)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # API docs generation
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        is_first = not Address.objects.filter(user=self.request.user).exists()
        address = serializer.save(user=self.request.user, is_default=serializer.validated_data.get("is_default") or is_first)
        self._single_default(address)

    @transaction.atomic
    def perform_update(self, serializer):
        self._single_default(serializer.save())

    def _single_default(self, address):
        if address.is_default:
            Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)


class CheckoutView(APIView):
    """Create an order from the cart. Stock is reserved until the payment deadline."""

    @extend_schema(request=CheckoutSerializer, responses={201: OrderSerializer})
    def post(self, request):
        payload = CheckoutSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        address = Address.objects.filter(pk=payload.validated_data["address_id"], user=request.user).first()
        if address is None:
            return Response({"detail": "نشانی پیدا نشد.", "code": "address_not_found"}, status=404)
        try:
            order = services.checkout(request.user, address, payload.validated_data["note"])
        except services.OrderError as exc:
            return _error(exc)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    lookup_field = "number"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # API docs generation
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    @extend_schema(request=None, responses=inline_serializer("PayResponse", {"payment_url": serializers.URLField()}))
    @action(detail=True, methods=["post"])
    def pay(self, request, number=None):
        """Get the bank payment page URL. The app opens it in the phone's browser."""
        order = self.get_object()
        callback = settings.PAYMENT_CALLBACK_URL or request.build_absolute_uri(reverse("payment-callback"))
        try:
            url = services.start_payment(order, callback, request=request)
        except services.OrderError as exc:
            return _error(exc)
        return Response({"payment_url": url})

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, number=None):
        try:
            order = services.cancel_order(self.get_object())
        except services.OrderError as exc:
            return _error(exc)
        return Response(OrderSerializer(order).data)


class AppRedirect(HttpResponseRedirect):
    """Allows redirecting the browser back into the mobile app (custom URL scheme)."""

    allowed_schemes = ["http", "https", settings.PAYMENT_RESULT_URL.split("://")[0]]


class PaymentCallbackView(APIView):
    """
    The bank sends the customer's browser here after payment. We verify the
    payment server-to-server, then send the browser back into the app.
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(exclude=True)
    def get(self, request):
        authority = request.query_params.get("Authority", "")
        try:
            order, success = services.complete_payment(authority, request.query_params)
            params = {"order": order.number, "status": "success" if success else "failed"}
        except services.OrderError:
            params = {"status": "failed"}
        return AppRedirect(f"{settings.PAYMENT_RESULT_URL}?{urlencode(params)}")


class SandboxPaymentPage(APIView):
    """Fake bank page for development (only works while SandboxGateway is active)."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    @extend_schema(exclude=True)
    def get(self, request, authority):
        if not isinstance(get_gateway(), SandboxGateway):
            raise Http404
        callback = escape(reverse("payment-callback"))
        auth = escape(authority)
        html = (
            '<html dir="rtl"><body style="font-family:sans-serif;text-align:center;padding:40px">'
            "<h2>درگاه آزمایشی — هیچ پولی جابه‌جا نمی‌شود</h2>"
            f'<p><a href="{callback}?Authority={auth}&Status=OK">پرداخت موفق</a></p>'
            f'<p><a href="{callback}?Authority={auth}&Status=NOK">پرداخت ناموفق</a></p>'
            "</body></html>"
        )
        return HttpResponse(html)
