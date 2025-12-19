from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from transcriber.models import Transcription
from transcriber.models.transcription import TranscriptionStatus
from transcriber.tasks import handle_transcripts
from transcriber.util import temp_path_of_uploaded_video

from .filters import TranscriptionFilter
from .serializers import TranscriptSerializer, VideoSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Transcripts"],
        operation_id="list_transcripts",
        summary="List Transcripts",
        description="Retrieve a list of transcripts for the authenticated user. Superusers can see all transcripts.",
        responses={200: TranscriptSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Transcripts"],
        operation_id="retrieve_transcripts",
        summary="Retrieve Transcript",
        description="Retrieve a transcript for the authenticated user. Superusers can see retrieve any transcript.",
        responses={200: TranscriptSerializer()},
    ),
    generate=extend_schema(
        tags=["Transcripts"],
        operation_id="generate_transcripts",
        summary="Generate Transcript",
        description="Generate a new transcript from an uploaded video file. The transcription process is handled asynchronously.",
        request=VideoSerializer,
        responses={200: TranscriptSerializer()},
    ),
)
class TranscriptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TranscriptSerializer
    queryset = Transcription.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TranscriptionFilter

    def get_queryset(self):
        if self.request.user.is_superuser:
            return super().get_queryset().order_by("-created_at")

        return super().get_queryset().filter(user=self.request.user).order_by("-created_at")

    @action(detail=False, methods=["post"])
    def generate(self, request):
        serializer = VideoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        temp_video_path = temp_path_of_uploaded_video(serializer.validated_data["video_file"])

        transcripts = Transcription.objects.create(status=TranscriptionStatus.PENDING, user=request.user)
        handle_transcripts.apply_async(args=[transcripts.id, temp_video_path])

        return Response(TranscriptSerializer(transcripts).data, status=status.HTTP_202_ACCEPTED)
