import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ffmpeg
import structlog
from celery import shared_task

from .llms.chairman import process_audio_with_gemini_council
from .llms.providers import get_available_transcribers
from .models.transcription import Transcription as Transcription
from .models.transcription import TranscriptionStatus
from .models.transcription_data import TranscriptionData as TranscriptionData
from .util import temp_srt_file_path

logger = structlog.get_logger(__name__)


# Define where to save stitched videos
STITCHED_VIDEOS_DIR = Path("stitched_videos")
STITCHED_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


@shared_task(bind=True, max_retries=3)
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
        with ThreadPoolExecutor(max_workers=len(transcribers)) as executor:
            future_map = {executor.submit(t.transcribe): t for t in transcribers}

            for future in as_completed(future_map):
                provider = future_map[future]
                provider_name = provider.__class__.__name__.replace("TranscriberLLM", "").lower()

                try:
                    raw_result = future.result()

                    text = provider.extract_text(raw_result)
                    segments = provider.extract_segments(raw_result)

                    results.update(
                        {
                            provider_name: {
                                "used_model": provider_name,
                                "generated_text": text,
                                "segments": segments,
                                "output_language": "en",
                            }
                        }
                    )
                    audio_file_path = provider.audio_path

                except Exception as exc:
                    logger.error("Transcription failed", provider=provider_name, error=str(exc))

        if results:
            result = process_audio_with_gemini_council(audio_file_path, results)
            transcription_data = TranscriptionData.objects.create(
                transcription_id=transcription_id,
                generated_text=result["generated_text"],
                segments=result.get("segments", []),
                used_model=result["evaluation"]["selected_provider"],
                output_language="en",  # FIXME
            )
            transcription.status = TranscriptionStatus.SUCCESS

            stitch_subtitle_and_video.apply_async(args=[transcription_data.id, video_path])
        else:
            transcription.status = TranscriptionStatus.FAILED

        transcription.save(update_fields=["status"])

    except Exception:
        transcription.status = TranscriptionStatus.FAILED
        transcription.save(update_fields=["status"])
        raise


@shared_task(bind=True, max_retries=3)
def stitch_subtitle_and_video(self, transcription_data_id: str, tmp_video_path: str) -> None:
    """
    Add sub-title to the video.
    """
    transcription_data = TranscriptionData.objects.get(id=transcription_data_id)
    segments = transcription_data.segments

    subtitle_file_path = temp_srt_file_path(segments)

    # FIXME: Upload video to S3
    output_filename = f"transcription_{str(transcription_data_id)}_with_subtitles.mp4"
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

    # Clean up subtitle file
    if os.path.exists(subtitle_file_path):
        os.unlink(subtitle_file_path)
