from django.urls import include, path

from .v1 import urlpatterns as v1_urlpatterns

urlpatterns = [
    path("v1/", include((v1_urlpatterns, "v1"), namespace="v1")),
]
