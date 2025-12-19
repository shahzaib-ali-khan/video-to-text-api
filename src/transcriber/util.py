import os
import tempfile

import magic
from django.core.files.uploadedfile import TemporaryUploadedFile


def temp_path_of_uploaded_video(video_file: TemporaryUploadedFile) -> str:
    """
    Upload video file to temp path and return
    Celery do not support receiving the file object itself
    """
    # validate MIME type
    video_file.seek(0)
    mime = magic.from_buffer(video_file.read(2048), mime=True)
    video_file.seek(0)

    if not mime.startswith("video/"):
        raise ValueError(f"Unsupported file type: {mime}")

    suffix = os.path.splitext(video_file.name)[1] or ".mp4"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="upload_")

    for chunk in video_file.chunks():
        temp_file.write(chunk)

    temp_file.close()
    return temp_file.name


def format_time(seconds: float) -> str:
    total_ms = int(seconds * 1000)

    ms = total_ms % 1000
    total_seconds = total_ms // 1000

    s = total_seconds % 60
    total_minutes = total_seconds // 60

    m = total_minutes % 60
    h = total_minutes // 60

    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def temp_srt_file_path(segments: list[dict]) -> str:
    """
    Create a temporary SRT file from segments and return its path.
    Each segment should be a dict with 'start', 'end', and 'text' keys.
    """
    temp_srt = tempfile.NamedTemporaryFile(delete=False, suffix=".srt", prefix="subs_")
    with open(temp_srt.name, "w", encoding="utf-8") as f:
        for idx, segment in enumerate(segments, start=1):
            f.write(f"{idx}\n")
            f.write(f"{format_time(segment['start'])} --> {format_time(segment['end'])}\n")
            f.write(f"{segment['text']}\n\n")

    return escape_subtitle_path_for_ffmpeg(temp_srt.name)


# ffmpeg-python library behaves weird on Windows path in filter
def escape_subtitle_path_for_ffmpeg(path: str) -> str:
    normalized = os.path.normpath(path)

    # Split drive and path
    drive, path_part = os.path.splitdrive(normalized)

    if not drive:
        # No drive letter (relative path or Unix-style)
        # Split by backslash and join with /\
        segments = path_part.strip("\\").split("\\")
        return "/\\".join(segments)

    # Remove the colon from drive letter
    drive_letter = drive.replace(":", "")

    # Split path into segments (remove leading/trailing backslashes)
    segments = path_part.strip("\\").split("\\")

    # Build the escaped path: C\\:/\segment1/\segment2/\segment3
    # Drive is escaped as "C\\:" and each path segment is prefixed with /\
    escaped_path = f"{drive_letter}\\\\:/" + "/".join(f"\\{seg}" for seg in segments)

    return escaped_path
