import pytest
from django.urls import reverse
from datetime import datetime

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
    assert Transcription.objects.get(id=response.data["id"]).status == "Success"


@pytest.mark.django_db
def test_transcription_list_pagination(api_client, transcription_pending_status, user):
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("v1:transcripts-list"))

    assert response.status_code == 200
    assert "results" in response.data
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == str(transcription_pending_status.id)


@pytest.mark.django_db
def test_transcription_success_filter(api_client, transcription_pending_status, transcription_success_status, user):
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("v1:transcripts-list"), {"status": "Success"})

    assert response.status_code == 200
    assert "results" in response.data
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["id"] == str(transcription_success_status.id)


@pytest.mark.django_db
def test_transcription_created_at_date_filter(
    api_client, transcription_pending_status, transcription_success_status, transcription_success_status_yesterday, user
):
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("v1:transcripts-list"), {"created_at__gte": datetime.now().date().isoformat()})

    assert response.status_code == 200
    assert "results" in response.data
    assert len(response.data["results"]) == 2
    assert not any(result["id"] == str(transcription_success_status_yesterday.id) for result in response.data["results"])
