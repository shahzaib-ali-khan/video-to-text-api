import json
from datetime import datetime, timedelta

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils.timezone import now
from rest_framework.test import APIClient

from transcriber.llms.assembly_ai import AssemblyTranscriberLLM
from transcriber.llms.open_ai import OpenAITranscriberLLM
from transcriber.models import Transcription
from transcriber.models.transcription import TranscriptionStatus
from transcriber.models.transcription_data import TranscriptionData

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
    django_settings.GEMINI_API_KEY = "foo-nord"

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


@pytest.fixture
def transcription_pending_status(user):
    return Transcription.objects.create(user=user, status=TranscriptionStatus.PENDING)


@pytest.fixture
def transcription_success_status(user):
    transcription = Transcription.objects.create(user=user, status=TranscriptionStatus.SUCCESS)
    TranscriptionData.objects.create(
        transcription=transcription,
        output_language="en",
        used_model="openai-whisper",
        generated_text="This is a successful transcription.",
        segments=[{"text": "This is a successful transcription.", "start": 0.0, "end": 5.0}],
    )
    return transcription


@pytest.fixture
def transcription_success_status_yesterday(user, freezer):
    now_ = now()
    # Move to yesterday
    freezer.move_to(datetime.now() - timedelta(days=1))

    transcription = Transcription.objects.create(user=user, status=TranscriptionStatus.SUCCESS)
    TranscriptionData.objects.create(
        transcription=transcription,
        output_language="en",
        used_model="openai-whisper",
        generated_text="This is a successful transcription.",
        segments=[{"text": "This is a successful transcription.", "start": 0.0, "end": 5.0}],
    )
    # Move freezr back to now
    freezer.move_to(now_)

    return transcription


@pytest.fixture
def mock_gemini_chairman(mocker):
    """
    Mock Gemini chairman evaluation response using google-genai SDK.
    """

    gemini_response_payload = {
        "audio_analysis": {
            "duration_estimate": "30 seconds",
            "audio_quality": "clear",
            "language_detected": "English",
            "key_observations": "Single speaker, neutral accent, no background noise",
        },
        "A": {
            "accuracy": {
                "score": 7,
                "reasoning": "Minor word omissions and tense errors",
                "errors_found": ["missing 's' in asks"],
            },
            "punctuation": {
                "score": 7,
                "reasoning": "Missing commas and sentence endings",
            },
            "formatting": {
                "score": 7,
                "reasoning": "Readable but lacks paragraph structure",
            },
            "completeness": {
                "score": 8,
                "reasoning": "Mostly complete",
                "missing_content": [],
                "hallucinated_content": [],
            },
            "timestamps": {
                "score": 7,
                "reasoning": "Mostly aligned",
            },
            "total_score": 0,
            "strengths": ["Clear wording"],
            "weaknesses": ["Grammar mistakes"],
        },
        "B": {
            "accuracy": {
                "score": 9,
                "reasoning": "Matches audio closely",
                "errors_found": [],
            },
            "punctuation": {
                "score": 8,
                "reasoning": "Mostly correct punctuation",
            },
            "formatting": {
                "score": 8,
                "reasoning": "Well structured",
            },
            "completeness": {
                "score": 9,
                "reasoning": "No missing content",
                "missing_content": [],
                "hallucinated_content": [],
            },
            "timestamps": {
                "score": 8,
                "reasoning": "Good alignment",
            },
            "total_score": 0,
            "strengths": ["High accuracy", "Good structure"],
            "weaknesses": ["Minor punctuation"],
        },
        "comparison": {
            "winner": "B",
            "confidence": "high",
            "score_difference": 1.6,
            "deciding_factors": ["Accuracy", "Completeness"],
        },
        "final_reasoning": "Transcription B aligns more closely with the spoken audio.",
        "recommendation": "Improve punctuation consistency in transcription A.",
    }

    # Gemini SDK returns an object with `.text`
    mock_response = mocker.MagicMock()
    mock_response.text = json.dumps(gemini_response_payload)

    # Patch the exact SDK call used in your code
    mocker.patch(
        "google.genai.models.Models.generate_content",
        return_value=mock_response,
    )

    return gemini_response_payload
