import json
from pathlib import Path
from typing import Dict

import structlog
from django.conf import settings
from google import genai
from google.genai import types

logger = structlog.get_logger(__name__)


# Configuration for Chairman to be used
class TranscriptionCouncilConfig:
    CHAIRMAN_MODEL = "gemini-2.5-flash"
    GEMINI_API_KEY = settings.GEMINI_API_KEY

    SUPPORTED_AUDIO_FORMATS = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }

    CRITERIA_WEIGHTS = {
        "accuracy": 0.40,
        "punctuation": 0.15,
        "formatting": 0.15,
        "completeness": 0.20,
        "timestamps": 0.10,
    }


class AudioFileHandler:
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        ext = Path(file_path).suffix.lower().lstrip(".")
        return TranscriptionCouncilConfig.SUPPORTED_AUDIO_FORMATS.get(ext, "audio/wav")

    @staticmethod
    def validate_audio_file(file_path: str) -> bool:
        ext = Path(file_path).suffix.lower().lstrip(".")
        return ext in TranscriptionCouncilConfig.SUPPORTED_AUDIO_FORMATS


class GeminiChairmanEvaluator:
    """
    Gemini-based chairman model that listens to audio and judges transcripts.
    """

    def __init__(self, api_key: str | None = None):
        self.client = genai.Client(api_key=api_key or TranscriptionCouncilConfig.GEMINI_API_KEY)
        self.audio_handler = AudioFileHandler()

    def evaluate_transcriptions(
        self,
        audio_file_path: str,
        audio_context: str,
        openai_result: dict | None = None,
        assemblyai_result: dict | None = None,
    ) -> dict:
        if not self.audio_handler.validate_audio_file(audio_file_path):
            raise ValueError("Unsupported audio format")

        mime_type = self.audio_handler.get_mime_type(audio_file_path)

        # Read audio bytes
        audio_bytes = Path(audio_file_path).read_bytes()

        prompt = self._create_evaluation_prompt(audio_context, openai_result, assemblyai_result)

        logger.info("Gemini Chairman is evaluating transcripts")

        # Upload the audio file with prompt for evaluation
        response = self.client.models.generate_content(
            model=TranscriptionCouncilConfig.CHAIRMAN_MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type=mime_type,
                        ),
                        types.Part.from_text(text=prompt),
                    ]
                )
            ],
            config=types.GenerateContentConfig(temperature=0.3),
        )

        return self._parse_evaluation(response.text)

    # Use A, B for anonymizing the input to chairman model
    def _create_evaluation_prompt(
        self,
        audio_context: str,
        openai_result: dict | None = None,
        assemblyai_result: dict | None = None,
    ) -> str:
        """
        Create an evaluation prompt for the chairman model (Gemini).

        The prompt is built dynamically and only includes transcription
        sections that are actually available.
        """

        if not audio_context:
            raise ValueError("audio_context must not be empty")

        sections: list[str] = []

        # ------------------------------------------------------------------
        # System instructions
        # ------------------------------------------------------------------
        sections.append(
            """You are an expert transcription evaluator.

    You are given:
    - An audio file
    - One or more AI-generated transcriptions of that audio

    Your responsibilities:
    1. LISTEN carefully to the audio
    2. COMPARE the transcription(s) against what is spoken
    3. EVALUATE accuracy, completeness, and clarity
    4. SELECT the best transcription if more than one is provided
    5. JUSTIFY your decision with concrete examples
    """
        )

        # ------------------------------------------------------------------
        # Audio context
        # ------------------------------------------------------------------
        sections.append(
            f"""AUDIO CONTEXT:
    {audio_context}
    """
        )

        available_transcriptions: list[str] = []

        # ------------------------------------------------------------------
        # OpenAI Whisper transcription
        # ------------------------------------------------------------------
        if openai_result:
            text = openai_result.get("text", "") or ""
            segments = openai_result.get("segments") or []

            sections.append(
                f"""TRANSCRIPTION A (OpenAI Whisper):

    Word Count: {len(text.split())}
    Has Timestamps: {bool(segments)}
    """
            )
            available_transcriptions.append("A")

        # ------------------------------------------------------------------
        # AssemblyAI transcription
        # ------------------------------------------------------------------
        if assemblyai_result:
            text = assemblyai_result.get("text", "") or ""
            segments = assemblyai_result.get("segments") or []

            sections.append(
                f"""TRANSCRIPTION B (AssemblyAI):

    Word Count: {len(text.split())}
    Has Timestamps: {bool(segments)}
    """
            )
            available_transcriptions.append("B")

        # ------------------------------------------------------------------
        # Guardrail
        # ------------------------------------------------------------------
        if not available_transcriptions:
            raise ValueError("At least one transcription (OpenAI or AssemblyAI) must be provided")

        # ------------------------------------------------------------------
        # Evaluation instructions
        # ------------------------------------------------------------------
        if len(available_transcriptions) == 1:
            sections.append(
                f"""EVALUATION INSTRUCTIONS:
    Only ONE transcription is provided (Transcription {available_transcriptions[0]}).

    Evaluate it against the audio for:
    - Verbatim accuracy
    - Missing or hallucinated words
    - Punctuation and sentence boundaries
    - Timestamp quality (if present)

    Do NOT invent comparisons or rankings.
    """
            )
        else:
            sections.append(
                """EVALUATION INSTRUCTIONS:
    Two transcriptions are provided.

    For EACH transcription:
    - Assess accuracy against the audio
    - Identify errors, omissions, and formatting issues

    Then:
    - Choose the BEST transcription overall
    - Clearly explain why it is superior
    """
            )

        # ------------------------------------------------------------------
        # Required JSON response format
        # ------------------------------------------------------------------
        sections.append(
            """YOUR RESPONSE MUST BE IN THIS EXACT JSON FORMAT (respond ONLY with valid JSON, no other text):
    
    Rules:
    - Do NOT include markdown
    - Do NOT include extra text outside JSON
    - Be objective and specific

    Schema:
    {
    "audio_analysis":{
        "duration_estimate":"X seconds",
        "audio_quality":"clear/moderate/poor",
        "language_detected":"English/Spanish/etc",
        "key_observations":"What you noticed about the audio (speaker count, accents, background noise, etc.)"
    },
    "A":{
        "accuracy":{
            "score":8,
            "reasoning":"Specific examples of correct/incorrect transcriptions",
            "errors_found":[
                "error 1",
                "error 2"
            ]
        },
        "punctuation":{
            "score":7,
            "reasoning":"Evaluation of punctuation quality"
        },
        "formatting":{
            "score":8,
            "reasoning":"Evaluation of formatting and structure"
        },
        "completeness":{
            "score":9,
            "reasoning":"Assessment of missing or extra content",
            "missing_content":[
                
            ],
            "hallucinated_content":[
                
            ]
        },
        "timestamps":{
            "score":8,
            "reasoning":"Timestamp accuracy assessment"
        },
        "total_score":0,
        "strengths":[
            "strength 1",
            "strength 2"
        ],
        "weaknesses":[
            "weakness 1",
            "weakness 2"
        ]
    },
    "B":{
        "accuracy":{
            "score":9,
            "reasoning":"Specific examples of correct/incorrect transcriptions",
            "errors_found":[
                "error 1"
            ]
        },
        "punctuation":{
            "score":8,
            "reasoning":"Evaluation of punctuation quality"
        },
        "formatting":{
            "score":7,
            "reasoning":"Evaluation of formatting and structure"
        },
        "completeness":{
            "score":8,
            "reasoning":"Assessment of missing or extra content",
            "missing_content":[
                
            ],
            "hallucinated_content":[
                
            ]
        },
        "timestamps":{
            "score":7,
            "reasoning":"Timestamp accuracy assessment"
        },
        "total_score":0,
        "strengths":[
            "strength 1",
            "strength 2"
        ],
        "weaknesses":[
            "weakness 1",
            "weakness 2"
        ]
    },
    "comparison":{
        "winner":"A",
        "confidence":"high",
        "score_difference":0,
        "deciding_factors":[
            "factor 1",
            "factor 2"
        ]
    },
    "final_reasoning":"Comprehensive explanation of why the winner was chosen based on your listening experience",
    "recommendation":"Any suggestions for improving either transcription"
    }
    """
        )

        return "\n".join(sections)

    def _parse_evaluation(self, text: str) -> dict:
        try:
            text = text.strip()
            evaluation = json.loads(text)

            weights = TranscriptionCouncilConfig.CRITERIA_WEIGHTS

            for key in ("A", "B"):
                if key in evaluation:
                    total = 0.0
                    for criterion, weight in weights.items():
                        score = evaluation[key].get(criterion, {}).get("score", 0)
                        total += score * weight
                    evaluation[key]["total_score"] = round(total, 2)

            a = evaluation["A"]["total_score"]
            b = evaluation["B"]["total_score"]

            evaluation.setdefault("comparison", {})
            evaluation["comparison"]["score_difference"] = round(abs(a - b), 2)

            return evaluation

        except Exception as e:
            return {
                "comparison": {"winner": "A", "confidence": "low"},
                "error": str(e),
                "raw_response": text[:1000],
            }


class TranscriptionCouncil:
    def __init__(self, gemini_api_key: str | None = None):
        self.chairman = GeminiChairmanEvaluator(gemini_api_key)

    def _prepare_audio_context(self, audio_file_path: str, metadata: Dict = None) -> str:
        """Prepare context information about the audio."""

        file_name = Path(audio_file_path).name
        file_size = Path(audio_file_path).stat().st_size / (1024 * 1024)  # MB

        context_parts = [f"File: {file_name}", f"Size: {file_size:.2f} MB"]

        # Use metadata also in evaluation in future
        if metadata:
            if "duration" in metadata:
                context_parts.append(f"Duration: {metadata['duration']} seconds")
            if "language" in metadata:
                context_parts.append(f"Language: {metadata['language']}")
            if "audio_type" in metadata:
                context_parts.append(f"Type: {metadata['audio_type']}")
            if "sample_rate" in metadata:
                context_parts.append(f"Sample Rate: {metadata['sample_rate']} Hz")

        return "\n".join(context_parts)

    def select_best_transcription(
        self,
        audio_file_path: str,
        openai_result: dict | None = None,
        assemblyai_result: dict | None = None,
        audio_metadata: dict | None = None,
    ) -> tuple[dict, dict]:
        audio_context = self._prepare_audio_context(audio_file_path, audio_metadata)

        evaluation = self.chairman.evaluate_transcriptions(
            audio_file_path,
            audio_context,
            openai_result,
            assemblyai_result,
        )

        # As fallback, use A as winner
        winner = evaluation.get("comparison", {}).get("winner", "A")

        # Set winner and provider. Chairman declare wineer to either A or B
        best = openai_result if winner == "A" else assemblyai_result
        provider = "OpenAI" if winner == "A" else "AssemblyAI"

        # Add result for the option to save in the database
        best["evaluation"] = {
            "selected_provider": provider,
            "confidence": evaluation.get("comparison", {}).get("confidence"),
            "score_difference": evaluation.get("comparison", {}).get("score_difference", 0),
            "final_reasoning": evaluation.get("final_reasoning"),
            "audio_analysis": evaluation.get("audio_analysis"),
        }

        return best, evaluation


def process_audio_with_gemini_council(audio_file_path: str, results: Dict[Dict], audio_metadata: Dict = None) -> Dict:
    """
    Process audio with OpenAI and AssemblyAI, then use Gemini to evaluate.
    """

    if not settings.GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set. Transcription generation cannot be proceed")

    logger.info("🎯 Starting Transcription Council Process (Gemini Chairman)...")

    council = TranscriptionCouncil(gemini_api_key=settings.GEMINI_API_KEY)
    openai_result = results.pop("openai", None)
    assemblyai_result = results.pop("assembly", None)

    best_result, evaluation = council.select_best_transcription(
        audio_file_path, openai_result, assemblyai_result, audio_metadata=audio_metadata
    )

    return best_result
