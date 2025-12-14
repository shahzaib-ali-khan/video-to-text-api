import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from transcriber.llms.assembly_ai import AssemblyTranscriberLLM
from transcriber.llms.open_ai import OpenAITranscriberLLM

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password123",
    )


@pytest.fixture
def set_dummy_api_key():
    AssemblyTranscriberLLM.API_KEY = "test-assembly-key"
    OpenAITranscriberLLM.API_KEY = "test-openai-key"


@pytest.fixture
def load_video_file():
    with open("tests/data/video.mp4", "rb") as f:
        return ContentFile(f.read(), name="video.mp4")


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def mock_assemblyai_transcribe(mocker):
    # Mock AssemblyAI SDK's transcribe method to return a predefined response
    mock_transcript = mocker.MagicMock()
    mock_transcript.status = "completed"
    mock_transcript.text = "This is a mocked transcript from AssemblyAI."
    mock_transcript.words = [
        mocker.MagicMock(text="This", start=100, end=300, confidence=0.99, speaker=None),
        mocker.MagicMock(text="is", start=320, end=500, confidence=0.98, speaker=None),
        mocker.MagicMock(text="a", start=520, end=700, confidence=0.99, speaker=None),
        mocker.MagicMock(text="mocked", start=720, end=1000, confidence=0.97, speaker=None),
        mocker.MagicMock(text="transcript", start=1020, end=1500, confidence=0.99, speaker=None),
    ]
    mock_transcript.error = None

    mocker.patch("assemblyai.Transcriber.transcribe", return_value=mock_transcript)

    return mock_transcript


@pytest.fixture
def mock_open_ai_transcription_create(mocker):
    # Create a mock response object matching verbose_json format
    mock_resp = mocker.MagicMock()
    mock_resp.text = "This is a mocked transcript from OpenAI."
    mock_resp.segments = [
        mocker.MagicMock(text="This", start=0.0, end=1.5),
        mocker.MagicMock(text="is", start=1.6, end=2.5),
        mocker.MagicMock(text="a", start=2.6, end=3.5),
        mocker.MagicMock(text="mocked", start=3.6, end=5.0),
        mocker.MagicMock(text="transcript", start=5.1, end=7.0),
    ]

    mocker.patch("openai.resources.audio.transcriptions.Transcriptions.create", return_value=mock_resp)

    return mock_resp
