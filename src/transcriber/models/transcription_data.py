import uuid

from django.db import models

from .transcription import Transcription


class TranscriptionData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    output_language = models.CharField(max_length=20, default="en")

    used_model = models.CharField(max_length=50)

    generated_text = models.TextField()
    segments = models.JSONField(default=list)

    transcription = models.ForeignKey(Transcription, on_delete=models.CASCADE, related_name="results")

    def __str__(self):
        return f"{self.provider}/{self.model} → {self.transcription_id}"
