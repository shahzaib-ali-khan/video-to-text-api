from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from transcriber.models import Transcription
from transcriber.models.transcription import TranscriptionStatus
from transcriber.tasks import handle_transcripts

from ..util import temp_path_of_uploaded_video
from .serializers import TranscriptionDataSerializer, TranscriptSerializer, VideoSerializer


class TranscriptsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TranscriptSerializer
    queryset = Transcription.objects.all()
    permission_classes = [IsAuthenticated]

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

    @action(detail=True, methods=["get"])
    def data(self, request, pk):
        transcripts_data = self.get_object().results.all()
        serializer = TranscriptionDataSerializer(transcripts_data, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
