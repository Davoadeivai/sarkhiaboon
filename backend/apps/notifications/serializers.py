from rest_framework import serializers

from .models import PushDevice


class PushDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=PushDevice.Platform.choices)


class PushDeviceRemoveSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
