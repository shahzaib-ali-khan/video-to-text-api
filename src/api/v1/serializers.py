from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from transcriber.models import Transcription
from transcriber.models.transcription_data import TranscriptionData


class VideoSerializer(serializers.Serializer):
    MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB

    video_file = serializers.FileField(
        required=True,
        allow_empty_file=False,
        max_length=None,
        use_url=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["mp4", "mov", "avi", "mkv", "webm", "m4v", "mpg", "mpeg"],
                message="Unsupported video format.",
            )
        ],
    )

    def validate(self, data):
        video_file = data["video_file"]
        if video_file.size > self.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                {"video_file": f"File too large: {video_file.size // (1024 * 1024)} MB (max 25 MB)"}
            )
        return data


class TranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = ["id", "created_at", "user", "status"]
        read_only_fields = fields


class TranscriptionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptionData
        fields = ["id", "created_at", "output_language", "used_model", "generated_text", "segments"]
        read_only_fields = fields
