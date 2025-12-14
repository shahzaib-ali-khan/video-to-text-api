import pytest
from django.urls import reverse

from transcriber.models import TranscriptionData, Transcription


@pytest.mark.django_db
def test_transcription_creation(
    api_client, load_video_file, mock_assemblyai_transcribe, mock_open_ai_transcription_create, user, set_dummy_api_key
):
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("v1:transcripts-generate"),
        {
            "video_file": load_video_file,
        },
        format="multipart",
    )

    assert response.status_code == 202
    assert "id" in response.data

    assert TranscriptionData.objects.filter(transcription_id=response.data["id"]).count() == 2
    assert Transcription.objects.get(id=response.data["id"]).status == "SUCCESS"
