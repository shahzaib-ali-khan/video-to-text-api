from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from transcriber.models import TranscriptionData

from .serializers import TranscriptionDataSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Transcript Data"],
        operation_id="list_transcript_data",
        summary="List Transcript Data",
        description="Retrieve a list of transcript data entries for the authenticated user. Superusers can see all transcript data.",
        parameters=[
            OpenApiParameter(
                name="transcript_pk",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            )
        ],
        responses={200: TranscriptionDataSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Transcript Data"],
        operation_id="retrieve_transcript_data",
        summary="Retrieve Transcript Data",
        description="Retrieve a transcript data entry for the authenticated user. Superusers can retrieve any transcript data.",
        parameters=[
            OpenApiParameter(
                name="transcript_pk",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            )
        ],
        responses={200: TranscriptionDataSerializer()},
    ),
    destroy=extend_schema(
        tags=["Transcript Data"],
        operation_id="delete_transcript_data",
        summary="Delete Transcript Data",
        description="Delete a transcript data entry for the authenticated user. Superusers can delete any transcript data.",
        parameters=[
            OpenApiParameter(
                name="transcript_pk",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            )
        ],
        responses={204: None},
    ),
)
class TranscriptDataViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin
):
    queryset = TranscriptionData.objects.all()
    serializer_class = TranscriptionDataSerializer
    permission_classes = [IsAuthenticated]


def get_queryset(self):
    transcript_id = self.kwargs.get("transcript_pk")

    if not transcript_id:
        raise ValueError("Transcript ID is required")

    qs = TranscriptionData.objects.filter(transcription_id=transcript_id)

    if self.request.user.is_superuser:
        return qs.order_by("-created_at")

    return qs.filter(transcription__user=self.request.user).order_by("-created_at")
