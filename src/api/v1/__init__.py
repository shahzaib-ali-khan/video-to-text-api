from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .transcript import TranscriptViewSet
from .transcript_data import TranscriptDataViewSet

router = DefaultRouter()
router.register("transcripts", TranscriptViewSet, basename="transcripts")

# Nested router
transcripts_router = NestedDefaultRouter(router, "transcripts", lookup="transcript")
transcripts_router.register("data", TranscriptDataViewSet, basename="transcript-data")

urlpatterns = router.urls + transcripts_router.urls
