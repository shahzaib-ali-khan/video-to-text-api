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
        config = aai.TranscriptionConfig(
            speech_models=["universal"],
            auto_highlights=False,
            entity_detection=False,
            sentiment_analysis=False,
            iab_categories=False,
            speaker_labels=False,
            summarization=False,
        )
        transcript = aai.Transcriber(config=config).transcribe(self.audio_path)

        if transcript.status == "error":
            raise RuntimeError(transcript.error)

        return {
            "provider": self.provider_name,
            "transcript": transcript.text,
            "words": transcript.words,
        }

    def extract_text(self, result: Any) -> dict:
        # AssemblyAI returns a dict that contains "transcript"
        return result.get("transcript", "")

    def extract_segments(self, result: Any) -> list[dict]:
        return [{"start": word.start / 1000, "end": word.end / 1000, "text": word.text} for word in result["words"]]
