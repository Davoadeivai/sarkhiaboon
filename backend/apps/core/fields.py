from rest_framework import serializers

from .utils import absolute_media_url


class MediaURLField(serializers.ImageField):
    """Image field that always serializes to a full URL the mobile app can load."""

    def to_representation(self, value):
        return absolute_media_url(value, self.context.get("request"))
