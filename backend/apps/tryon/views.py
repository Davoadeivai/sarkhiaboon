from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .imaging import PhotoRejected
from .models import PersonPhoto, TryOnJob
from .serializers import (
    PersonPhotoSerializer,
    PersonPhotoUploadSerializer,
    QuotaSerializer,
    TryOnJobCreateSerializer,
    TryOnJobSerializer,
)


def _error(exc):
    return Response({"detail": str(exc), "code": exc.code}, status=exc.status)


class PersonPhotoViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    The customer's own photos.
    POST (multipart, field 'image') uploads and validates a photo.
    DELETE removes it immediately (the customer can always delete their photo).
    """

    serializer_class = PersonPhotoSerializer
    parser_classes = (MultiPartParser, FormParser)
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # API docs generation
            return PersonPhoto.objects.none()
        return PersonPhoto.objects.live().filter(user=self.request.user)

    @extend_schema(request={"multipart/form-data": PersonPhotoUploadSerializer}, responses={201: PersonPhotoSerializer})
    def create(self, request):
        upload = PersonPhotoUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        try:
            photo = services.upload_person_photo(request.user, upload.validated_data["image"])
        except PhotoRejected as exc:
            return Response({"detail": str(exc), "code": "photo_rejected"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(photo).data, status=status.HTTP_201_CREATED)


class TryOnJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    POST   /jobs/                 start a try-on {product_id, photo_id} -> 202 (or 200 if served from cache)
    GET    /jobs/<id>/            poll status until 'completed' or 'failed'
    GET    /jobs/?saved=true      virtual wardrobe (saved results)
    POST   /jobs/<id>/save/       add to wardrobe;  DELETE removes
    DELETE /jobs/<id>/            delete from history
    """

    serializer_class = TryOnJobSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # API docs generation
            return TryOnJob.objects.none()
        qs = TryOnJob.objects.filter(user=self.request.user).select_related("product")
        if self.action == "list":
            saved = self.request.query_params.get("saved")
            if saved in ("true", "1"):
                qs = qs.filter(is_saved=True, status=TryOnJob.Status.COMPLETED)
        return qs

    @extend_schema(
        parameters=[OpenApiParameter("saved", bool, description="فقط موارد ذخیره‌شده در کمد مجازی")],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=TryOnJobCreateSerializer, responses={202: TryOnJobSerializer, 200: TryOnJobSerializer})
    def create(self, request):
        payload = TryOnJobCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        photo = PersonPhoto.objects.filter(pk=payload.validated_data["photo_id"], user=request.user).first()
        if photo is None:
            return Response({"detail": "عکس پیدا نشد.", "code": "photo_not_found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            job = services.create_job(request.user, payload.validated_data["product"], photo)
        except services.TryOnNotAllowed as exc:
            return _error(exc)
        # 200 when answered instantly from the result cache, otherwise 202:
        # the app then polls GET /jobs/<id>/ until the job is finished.
        code = status.HTTP_200_OK if job.is_finished else status.HTTP_202_ACCEPTED
        return Response(self.get_serializer(job).data, status=code)

    @extend_schema(request=None, responses=TryOnJobSerializer)
    @action(detail=True, methods=["post", "delete"])
    def save(self, request, pk=None):
        job = self.get_object()
        if request.method == "POST":
            if job.status != TryOnJob.Status.COMPLETED:
                return Response({"detail": "فقط پروهای کامل‌شده قابل ذخیره هستند."}, status=status.HTTP_400_BAD_REQUEST)
            job.is_saved = True
        else:
            job.is_saved = False
        job.save(update_fields=["is_saved"])
        return Response(self.get_serializer(job).data)


class QuotaView(APIView):
    """How many try-ons the user has left today."""

    @extend_schema(responses=QuotaSerializer)
    def get(self, request):
        quota = services.get_quota(request.user)
        return Response({"limit": quota.limit, "used": quota.used, "remaining": quota.remaining})
