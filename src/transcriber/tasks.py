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
        if not transcribers:
            logger.warning("No transcription providers available")
            transcription.status = TranscriptionStatus.FAILED
            transcription.save(update_fields=["status"])
            return

        success_count = 0
        with ThreadPoolExecutor(max_workers=len(transcribers)) as executor:
            future_map = {executor.submit(t.transcribe): t for t in transcribers}

            for future in as_completed(future_map):
                provider = future_map[future]
                provider_name = provider.__class__.__name__.replace("TranscriberLLM", "").lower()

                try:
                    raw_result = future.result()

                    # NEW: delegate extraction/normalization to provider
                    text = provider.extract_text(raw_result)
                    segments = provider.extract_segments(raw_result)

                    TranscriptionData.objects.create(
                        transcription_id=transcription_id,
                        used_model=provider_name,
                        generated_text=text,
                        segments=segments,
                        output_language="en",  # FIXME
                    )
                    success_count += 1

                except Exception as exc:
                    logger.error("Transcription failed", provider=provider_name, error=str(exc))

        # Success if at least one provider succeeded
        transcription.status = TranscriptionStatus.SUCCESS if success_count > 0 else TranscriptionStatus.FAILED
        transcription.save(update_fields=["status"])

    except Exception:
        transcription.status = TranscriptionStatus.FAILED
        transcription.save(update_fields=["status"])
        raise

    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)
            logger.info("Temporary video file deleted", path=video_path)
