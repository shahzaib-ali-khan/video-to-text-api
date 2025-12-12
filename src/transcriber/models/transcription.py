import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django_enum import EnumField


class TranscriptionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class Transcription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    status = EnumField(
        TranscriptionStatus,
        null=False,
        blank=False,
        default=TranscriptionStatus.PENDING,
    )
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return f"{self.user.username} - {self.id} Transcription"
