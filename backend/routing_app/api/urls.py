from django.urls import path

from .views import AnalyzeView, GeocodeView, HealthView

urlpatterns = [
    path("health", HealthView.as_view()),
    path("geocode", GeocodeView.as_view()),
    path("analyze", AnalyzeView.as_view()),
]
