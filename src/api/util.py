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
