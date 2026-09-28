from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .phone import normalize_phone, validate_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone=None, password=None, **extra_fields):
        if phone:
            phone = normalize_phone(phone)
        elif not extra_fields.get("is_guest"):
            raise ValueError("A phone number is required for non-guest users.")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_guest(self):
        return self.create_user(phone=None, is_guest=True)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone=phone, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Customers sign in with their mobile number and a one-time code; they never
    set a password. Staff users (admin panel) sign in with phone + password.

    Guest users have no phone. They exist so people can try the app before
    registering; when they verify a phone later, their data is kept (see
    services.login_with_phone).
    """

    phone = models.CharField(
        "شماره موبایل", max_length=11, unique=True, null=True, blank=True, validators=[validate_phone]
    )
    first_name = models.CharField("نام", max_length=60, blank=True)
    last_name = models.CharField("نام خانوادگی", max_length=80, blank=True)
    is_guest = models.BooleanField("کاربر مهمان", default=False)
    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField("کارمند", default=False)
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        if self.is_guest:
            return f"مهمان #{self.pk}"
        return self.phone or f"کاربر #{self.pk}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class OTPCode(models.Model):
    """
    One-time login code. Only an HMAC of the code is stored, so a leaked
    database does not reveal valid codes.
    """

    phone = models.CharField("شماره موبایل", max_length=11, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "کد ورود"
        verbose_name_plural = "کدهای ورود"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.phone} @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
