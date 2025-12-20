import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ffmpeg
import structlog
from celery import shared_task
from requests.exceptions import ConnectionError, Timeout

from .llms.chairman import process_audio_with_gemini_council
from .llms.providers import get_available_transcribers
from .models.transcription import Transcription
from .models.transcription import TranscriptionStatus
from .models.transcription_data import TranscriptionData
from .util import temp_srt_file_path

logger = structlog.get_logger(__name__)


# Define where to save stitched videos
STITCHED_VIDEOS_DIR = Path("stitched_videos")
STITCHED_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


TRANSIENT_EXCEPTIONS = (Timeout, ConnectionError)


@shared_task(bind=True, max_retries=3, retry_backoff=True, retry_backoff_max=60, retry_jitter=True)
def handle_transcripts(self, transcription_id: str, video_path: str):
    """
    Runs ALL transcription providers concurrently and stores their results
    under TranscriptionData.
    """
    logger.info(f"Handling transcripts for {transcription_id}")

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

        results = {}
        audio_file_path = None
        provider_errors = []

        with ThreadPoolExecutor(max_workers=len(transcribers)) as executor:
            future_map = {executor.submit(t.transcribe): t for t in transcribers}

            for future in as_completed(future_map):
                provider = future_map[future]
                provider_name = provider.__class__.__name__.replace("TranscriberLLM", "").lower()

                try:
                    raw_result = future.result()

                    text = provider.extract_text(raw_result)
                    segments = provider.extract_segments(raw_result)

                    results[provider_name] = {
                        "used_model": provider_name,
                        "generated_text": text,
                        "segments": segments,
                        "output_language": "en",
                    }
                    audio_file_path = provider.audio_path

                except TRANSIENT_EXCEPTIONS as exc:
                    logger.warning(
                        "Transient provider failure",
                        provider=provider_name,
                        error=str(exc),
                    )
                    provider_errors.append(exc)

                except Exception as exc:
                    # Permanent provider failure – do not retry
                    logger.error(
                        "Permanent provider failure",
                        provider=provider_name,
                        error=str(exc),
                    )

        # If nothing succeeded AND we saw transient failures → retry
        if not results and provider_errors:
            raise provider_errors[0]

        if not results:
            transcription.status = TranscriptionStatus.FAILED
            transcription.save(update_fields=["status"])
            return

        # ---- Gemini Council (external dependency) ----
        try:
            result = process_audio_with_gemini_council(
                audio_file_path,
                results,
            )
        except TRANSIENT_EXCEPTIONS as exc:
            logger.warning(
                "Gemini council temporarily unavailable",
                error=str(exc),
            )
            raise

        transcription_data, _ = TranscriptionData.objects.get_or_create(
            transcription_id=transcription_id,
            defaults={
                "generated_text": result["generated_text"],
                "segments": result.get("segments", []),
                "used_model": result["evaluation"]["selected_provider"],
                "output_language": "en",
            },
        )

        transcription.status = TranscriptionStatus.SUCCESS
        transcription.save(update_fields=["status"])

        stitch_subtitle_and_video.apply_async(args=[transcription_data.id, video_path])

    except TRANSIENT_EXCEPTIONS as exc:
        logger.warning(
            "Retrying handle_transcripts",
            transcription_id=transcription_id,
            retries=self.request.retries,
            error=str(exc),
        )
        raise self.retry(exc=exc)

    except Exception:
        logger.exception("Permanent failure in handle_transcripts")
        transcription.status = TranscriptionStatus.FAILED
        transcription.save(update_fields=["status"])
        raise


@shared_task(bind=True, max_retries=3, retry_backoff=True, retry_backoff_max=30, retry_jitter=True)
def stitch_subtitle_and_video(self, transcription_data_id: str, tmp_video_path: str) -> None:
    """
    Add sub-title to the video.
    """
    try:
        transcription_data = TranscriptionData.objects.get(id=transcription_data_id)
        segments = transcription_data.segments

        subtitle_file_path = temp_srt_file_path(segments)

        # FIXME: Upload video to S3
        output_filename = f"transcription_{transcription_data_id}_with_subtitles.mp4"
        output_video_path = str(STITCHED_VIDEOS_DIR / output_filename)

        (
            ffmpeg.input(tmp_video_path)
            .output(
                output_video_path,
                vf=f"subtitles={subtitle_file_path}",
                vcodec="libx264",
                acodec="aac",
                movflags="+faststart",
            )
            .run(overwrite_output=True)
        )

    except Exception as exc:
        logger.warning(
            "Retrying stitch_subtitle_and_video",
            transcription_data_id=transcription_data_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)

    finally:
        if "subtitle_file_path" in locals() and os.path.exists(subtitle_file_path):
            os.unlink(subtitle_file_path)
