from rest_framework.routers import DefaultRouter

from .transcript import TranscriptsViewSet

router = DefaultRouter()

router.register("transcripts", TranscriptsViewSet, basename="transcripts")

urlpatterns = router.urls
