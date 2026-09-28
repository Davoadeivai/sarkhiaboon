from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .phone import normalize_phone


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)


class OTPRequestSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)


class OTPVerifySerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    code = serializers.CharField(max_length=10)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "is_guest", "date_joined")
        read_only_fields = ("id", "phone", "is_guest", "date_joined")


class AuthResponseSerializer(serializers.Serializer):
    """Shape of every successful login response (documented for the app developer)."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    is_new_user = serializers.BooleanField()
    user = UserSerializer()


def build_auth_response(user, is_new_user=False):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "is_new_user": is_new_user,
        "user": UserSerializer(user).data,
    }
