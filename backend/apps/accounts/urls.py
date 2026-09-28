from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import GuestLoginView, MeView, OTPRequestView, OTPVerifyView

urlpatterns = [
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("guest/", GuestLoginView.as_view(), name="guest-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
