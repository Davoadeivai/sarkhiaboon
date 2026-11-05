from django.urls import path

from .views import PushDeviceView

urlpatterns = [path("devices/", PushDeviceView.as_view(), name="push-device")]
