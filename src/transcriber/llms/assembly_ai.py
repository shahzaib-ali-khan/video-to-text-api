from typing import Any

import assemblyai as aai

from backend import settings

from .base import TranscriberLLM


class AssemblyTranscriberLLM(TranscriberLLM):
    API_KEY = settings.ASSEMBLY_AI_API_KEY

    @property
    def provider_name(self):
        return "assemblyai"

    def transcribe(self) -> dict:
        aai.settings.api_key = self.API_KEY
        config = aai.TranscriptionConfig(speech_models=["universal"])
        transcript = aai.Transcriber(config=config).transcribe(self.audio_path)

        if transcript.status == "error":
            raise RuntimeError(transcript.error)

        return {"provider": self.provider_name, "transcript": transcript.text, "raw_response": transcript.__dict__}

    def extract_result(self, result: Any) -> dict:
        # AssemblyAI returns a dict that contains "transcript"
        text = result.get("transcript", "")

        return {"text": text}
