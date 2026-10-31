from __future__ import annotations

from django.conf import settings
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from ..domain.types import Place
from ..errors import ConfigError, InputError, UpstreamError
from ..pipeline import AnalyzeInput, analyze
from ..services.factory import get_geocoder, get_routing_provider, get_weather_provider
from ..services.geocoding import cached_search
from .errors import error_response
from .presenters import present_analysis
from .serializers import AnalyzeRequestSerializer

HANDLED_ERRORS = (InputError, UpstreamError, ConfigError)


def _resolve_place(value: dict) -> Place:
    """Accept a ready {lat, lon, label} or geocode a free-text query (first match wins)."""
    if "query" in value:
        matches = cached_search(get_geocoder(), value["query"], limit=1)
        if not matches:
            raise InputError(f"Couldn't find a place matching '{value['query']}'")
        return matches[0]
    return Place(lat=value["lat"], lon=value["lon"], label=value.get("label", ""))


class HealthView(APIView):
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "providers": {
                    "routing": settings.ROUTING_PROVIDER,
                    "geocoding": settings.GEOCODING_PROVIDER,
                    "weather": settings.WEATHER_PROVIDER,
                },
            }
        )


class GeocodeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "geocode"

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"results": []})
        try:
            places = cached_search(get_geocoder(), query)
        except HANDLED_ERRORS as exc:
            return error_response(exc)
        return Response({"results": [{"label": p.label, "lat": p.lat, "lon": p.lon} for p in places]})


class AnalyzeView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "analyze"

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = analyze(
                AnalyzeInput(
                    origin=_resolve_place(data["origin"]),
                    destination=_resolve_place(data["destination"]),
                    departure=data["departure"],
                    load_lb=data["load_lb"],
                    interval_miles=data["interval_miles"],
                ),
                routing=get_routing_provider(),
                weather=get_weather_provider(),
            )
        except HANDLED_ERRORS as exc:
            return error_response(exc)
        return Response(present_analysis(result))
