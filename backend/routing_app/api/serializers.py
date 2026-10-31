from __future__ import annotations

from rest_framework import serializers

from ..domain.checkpoints import ALLOWED_INTERVALS

MAX_LOAD_LB = 120_000  # well beyond any legal US gross weight; just a sanity bound


class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(required=False, allow_blank=True, default="", max_length=300)


class PlaceField(serializers.Field):
    """Either {"lat", "lon", "label"} or a free-text string that the server geocodes."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            text = data.strip()
            if len(text) < 2:
                raise serializers.ValidationError("Enter at least 2 characters.")
            return {"query": text}
        if isinstance(data, dict):
            nested = PlaceSerializer(data=data)
            nested.is_valid(raise_exception=True)
            return dict(nested.validated_data)
        raise serializers.ValidationError("Expected a place object or a text query.")

    def to_representation(self, value):
        return value


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = PlaceField()
    destination = PlaceField()
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
    interval_miles = serializers.ChoiceField(
        choices=list(ALLOWED_INTERVALS), required=False, allow_null=True, default=None
    )
