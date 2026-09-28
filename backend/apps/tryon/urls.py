from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import PersonPhotoViewSet, QuotaView, TryOnJobViewSet

router = SimpleRouter()
router.register("photos", PersonPhotoViewSet, basename="person-photo")
router.register("jobs", TryOnJobViewSet, basename="tryon-job")

urlpatterns = [path("quota/", QuotaView.as_view(), name="tryon-quota")] + router.urls
