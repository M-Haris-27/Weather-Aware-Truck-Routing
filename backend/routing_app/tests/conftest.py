import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Weather/geocode caches and throttles live in the default cache; isolate each test."""
    cache.clear()
    yield
    cache.clear()
