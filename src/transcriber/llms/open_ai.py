from typing import Any

from openai import OpenAI

from backend import settings

from .base import TranscriberLLM


class OpenAITranscriberLLM(TranscriberLLM):
    API_KEY = settings.OPEN_AI_API_KEY

    @property
    def provider_name(self):
        return "openai"

    def transcribe(self) -> dict:
        client = OpenAI(api_key=self.API_KEY)

        with open(self.audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1", file=f, response_format="verbose_json", timestamp_granularities=["segment"]
            )

        return {"provider": self.provider_name, "transcript": resp.text, "segments": resp.segments}

    def extract_text(self, result: Any) -> str:
        return result.get("transcript", "")

    def extract_segments(self, result: Any) -> list[dict]:
        return [{"start": seg.start, "end": seg.end, "text": seg.text.strip()} for seg in result["segments"]]
