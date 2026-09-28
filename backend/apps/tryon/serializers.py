from rest_framework import serializers

from apps.catalog.models import Product
from apps.core.fields import MediaURLField

from .models import PersonPhoto, TryOnJob


class PersonPhotoUploadSerializer(serializers.Serializer):
    image = serializers.FileField()


class PersonPhotoSerializer(serializers.ModelSerializer):
    image = MediaURLField(read_only=True)

    class Meta:
        model = PersonPhoto
        fields = ("id", "image", "width", "height", "created_at", "expires_at")


class TryOnProductSerializer(serializers.ModelSerializer):
    image = MediaURLField(read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "slug", "image", "price")


class TryOnJobCreateSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.visible(), source="product")
    photo_id = serializers.UUIDField()


class TryOnJobSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    queue_position = serializers.SerializerMethodField()
    result_image = MediaURLField(read_only=True)
    product = TryOnProductSerializer(read_only=True)

    class Meta:
        model = TryOnJob
        fields = (
            "id", "status", "status_label", "queue_position", "product", "tryon_type",
            "result_image", "error_message", "generation_seconds", "from_cache",
            "is_saved", "created_at", "finished_at",
        )

    def get_queue_position(self, obj) -> int | None:
        return obj.queue_position()


class QuotaSerializer(serializers.Serializer):
    limit = serializers.IntegerField()
    used = serializers.IntegerField()
    remaining = serializers.IntegerField()
