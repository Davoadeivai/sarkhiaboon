from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushDevice
from .serializers import PushDeviceRemoveSerializer, PushDeviceSerializer


class PushDeviceView(APIView):
    """The app registers its push token after login (guest or user) and removes it on logout."""

    @extend_schema(request=PushDeviceSerializer, responses={204: None}, summary="ثبت دستگاه برای اعلان")
    def post(self, request):
        data = PushDeviceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        # One token = one app install: it always belongs to whoever is logged in on that phone now.
        PushDevice.objects.update_or_create(
            token=data.validated_data["token"],
            defaults={"user": request.user, "platform": data.validated_data["platform"], "is_active": True},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=PushDeviceRemoveSerializer, responses={204: None}, summary="حذف دستگاه (خروج از حساب)")
    def delete(self, request):
        data = PushDeviceRemoveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        PushDevice.objects.filter(user=request.user, token=data.validated_data["token"]).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
