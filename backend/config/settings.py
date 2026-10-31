"""Django settings. Everything environment-specific comes from env vars (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "routing_app",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# The app is stateless: no models, so no database is needed.
DATABASES = {}

USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

# Per-process cache. Swap for Redis/Memcached if you run several workers.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    # No users in this app; this also stops DRF importing django.contrib.auth models.
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_RATES": {
        "analyze": os.environ.get("THROTTLE_ANALYZE", "30/min"),
        "geocode": os.environ.get("THROTTLE_GEOCODE", "120/min"),
    },
    "EXCEPTION_HANDLER": "routing_app.api.errors.exception_handler",
}

# --- Provider configuration -------------------------------------------------
ROUTING_PROVIDER = os.environ.get("ROUTING_PROVIDER", "mock").lower()
GEOCODING_PROVIDER = os.environ.get("GEOCODING_PROVIDER", ROUTING_PROVIDER).lower()
WEATHER_PROVIDER = os.environ.get("WEATHER_PROVIDER", "open_meteo").lower()

MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")
GEOCODING_COUNTRY = os.environ.get("GEOCODING_COUNTRY", "")
WEATHER_CACHE_TTL_SECONDS = int(os.environ.get("WEATHER_CACHE_TTL_SECONDS", "1800"))
