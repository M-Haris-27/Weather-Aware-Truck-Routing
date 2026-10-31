from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from ..errors import ConfigError, InputError, UpstreamError


def error_response(exc: Exception) -> Response:
    """Map our domain exceptions to a consistent {"error": "..."} JSON body."""
    if isinstance(exc, InputError):
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, UpstreamError):
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    if isinstance(exc, ConfigError):
        return Response({"error": f"Server is not configured: {exc}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    raise exc


def exception_handler(exc, context):
    """DRF hook: wrap validation errors as {"error": "Invalid request", "details": {...}}."""
    response = drf_exception_handler(exc, context)
    if response is not None and response.status_code == status.HTTP_400_BAD_REQUEST:
        response.data = {"error": "Invalid request", "details": response.data}
    return response
