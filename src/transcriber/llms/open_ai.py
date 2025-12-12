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
            resp = client.audio.transcriptions.create(model="whisper-1", file=f, response_format="json")

        return {"provider": self.provider_name, "transcript": resp.get("text", ""), "raw_response": resp}

    def extract_result(self, result: Any) -> dict:
        text = result["text"]
        # result from OpenAI is already JSON-serializable
        return {"text": text}
