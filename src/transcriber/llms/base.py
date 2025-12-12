from abc import ABC, abstractmethod
from typing import Any

import ffmpeg


class TranscriberLLM(ABC):
    """
    Abstract base class for any transcription provider.
    Defines shared behavior and interface (SOLID).
    """

    API_KEY = None

    def __init__(self, video_path: str):
        self.video_path = video_path
        self._validate_api_key()

    def _validate_api_key(self):
        if not self.API_KEY:
            raise ValueError(f"{self.__class__.__name__}: API_KEY is missing.")

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
    def extract_result(self, result: Any) -> dict:
        """Extract and normalize the transcription result from raw provider output."""
        pass
