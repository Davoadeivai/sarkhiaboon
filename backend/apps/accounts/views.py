from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.authentication import OptionalJWTAuthentication

from . import services
from .models import User
from .serializers import (
    AuthResponseSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    UserSerializer,
    build_auth_response,
)


class OTPRequestView(APIView):
    """Step 1 of login: send a one-time code to the phone number."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "otp_request"

    @extend_schema(
        request=OTPRequestSerializer,
        responses=inline_serializer("OTPRequestResponse", {"detail": serializers.CharField(), "expires_in": serializers.IntegerField()}),
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            expires_in = services.request_otp(serializer.validated_data["phone"])
        except services.OTPCooldownError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except services.OTPDeliveryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "کد ورود ارسال شد.", "expires_in": expires_in})


class OTPVerifyView(APIView):
    """
    Step 2 of login: verify the code and receive JWT tokens.
    If called with a guest token, the guest's data is kept.
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = (OptionalJWTAuthentication,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "otp_verify"

    @extend_schema(request=OTPVerifySerializer, responses=AuthResponseSerializer)
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            phone = services.verify_otp(serializer.validated_data["phone"], serializer.validated_data["code"])
            user, is_new = services.login_with_phone(phone, current_user=request.user)
        except services.OTPError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(build_auth_response(user, is_new_user=is_new))


class GuestLoginView(APIView):
    """Create a guest account so the user can browse and try on before registering."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "guest_login"

    @extend_schema(request=None, responses=AuthResponseSerializer)
    def post(self, request):
        user = User.objects.create_guest()
        return Response(build_auth_response(user, is_new_user=True), status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    """Current user's profile (name fields are editable)."""

    serializer_class = UserSerializer
    http_method_names = ("get", "patch")

    def get_object(self):
        return self.request.user
