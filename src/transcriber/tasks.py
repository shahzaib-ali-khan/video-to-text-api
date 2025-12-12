import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog
from celery import shared_task

from .llms.providers import get_available_transcribers
from .models.transcription import Transcription as Transcription
from .models.transcription import TranscriptionStatus
from .models.transcription_data import TranscriptionData as TranscriptionData

logger = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def handle_transcripts(self, transcription_id: str, video_path: str):
    """
    Runs ALL transcription providers concurrently and stores their results
    under TranscriptionData.
    """
    transcription = Transcription.objects.get(id=transcription_id)
    transcription.status = TranscriptionStatus.PROCESSING
    transcription.save(update_fields=["status"])

    try:
        transcribers = get_available_transcribers(video_path)

        with ThreadPoolExecutor(max_workers=len(transcribers)) as executor:
            future_map = {executor.submit(t.transcribe): t for t in transcribers}

            for future in as_completed(future_map):
                provider = future_map[future]
                provider_name = provider.__class__.__name__.replace("TranscriberLLM", "").lower()

                try:
                    raw_result = future.result()

                    # NEW: delegate extraction/normalization to provider
                    extracted = provider.extract_result(raw_result)
                    text = extracted["text"]

                    TranscriptionData.objects.create(
                        transcription_id=transcription_id,
                        used_model=provider_name,
                        generated_text=text.encode("utf-8"),
                        output_language="en",  # FIXME
                    )

                except Exception as exc:
                    logger.error("Transcription failed", provider=provider_name, error=str(exc))

        # Mark as finished (even if some providers failed)
        transcription.status = TranscriptionStatus.SUCCESS
        transcription.save(update_fields=["status"])

    except Exception:
        transcription.status = TranscriptionStatus.FAILED
        transcription.save(update_fields=["status"])
        raise

    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)
            logger.info("Temporary video file deleted", path=video_path)