from abc import ABC, abstractmethod
from typing import Any

import ffmpeg
import structlog

logger = structlog.get_logger(__name__)


class TranscriberLLM(ABC):
    """
    Abstract base class for any transcription provider.
    Defines shared behavior and interface (SOLID).
    """

    API_KEY = None

    def __init__(self, video_path: str):
        self.video_path = video_path

    @classmethod
    def is_configured(cls) -> bool:
        """
        Return True if the provider is usable (API key present).
        """
        if not cls.API_KEY:
            logger.warning(
                "Transcriber provider not configured",
                provider=cls.__name__,
                reason="API_KEY missing",
            )
            return False
        return True

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    def audio_path(self) -> str:
        """Extract audio from video into WAV using FFmpeg."""
        audio_path = self.video_path.rsplit(".", 1)[0] + ".wav"

        try:
            (
                ffmpeg.input(self.video_path)
                .output(audio_path, acodec="pcm_s16le", vn=None)
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as e:
            error = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"FFmpeg conversion failed: {error}")

        return audio_path

    @abstractmethod
    def transcribe(self) -> dict:
        """Return a JSON-serializable dict containing transcript result."""
        pass

    @abstractmethod
    def extract_text(self, result: Any) -> str:
        """Extract the transcription text from provider output."""
        pass

    @abstractmethod
    def extract_segments(self, result: Any) -> list[dict]:
        """Extract the transcription with segment from provider output."""
        pass
