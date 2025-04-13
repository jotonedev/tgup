import logging
import mimetypes
import tempfile
from functools import lru_cache
from pathlib import Path

from ffmpeg import FFmpegError
from ffmpeg.asyncio import FFmpeg

__all__ = ["is_video_type", "is_video_mp4", "extract_thumbnail"]

log = logging.getLogger(__name__)


@lru_cache
def get_mime_type(file_path: Path) -> str:
    return mimetypes.guess_file_type(file_path)[0]


def is_video_type(file_path: Path) -> bool:
    """
    Check if the file is a video.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is a video, False otherwise.
    """
    # Get the mime type based on the file extension
    mime_type = get_mime_type(file_path)

    # Check if mime_type is not None and starts with 'video/'
    return mime_type is not None and mime_type.startswith("video/")


def is_video_mp4(file_path: Path) -> bool:
    """
    Check if the file is a mp4 video.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is a mp4 video, False otherwise.
    """
    # Get the mime type based on the file extension
    mime_type = get_mime_type(file_path)

    # Check if it's specifically video/mp4
    return mime_type == "video/mp4"


async def extract_thumbnail(video_path: Path) -> bytes | None:
    """
    Extract the thumbnail from the video file.
    If it does not exist, create it from the first frame of the video.

    Args:
        video_path: Path to the video file.

    Returns:
        The thumbnail encoded in jpeg format.
    """
    # Check if the video file exists
    if not video_path.exists():
        raise FileNotFoundError(f"Video file {video_path} does not exist.")

    # Create tempfile
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete_on_close=False)
    temp_file.close()
    temp_file_path = Path(temp_file.name)

    # Check if the `attached_pic` exists
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(video_path)
        .output(temp_file_path, map="disp:attached_pic", codec="mjpeg")
    )
    try:
        log.debug(f"Extracting thumbnail from {video_path}")
        await ffmpeg.execute()
    except FFmpegError as e:
        log.warning(
            "Video does not contain an attached picture (thumbnail), generating one."
        )
        log.debug(f"FFMPEG error: {e.message}")
        log.debug(f"Arguments to execute ffmpeg: {' '.join(e.arguments)}")
    else:
        log.info(f"Extracted thumbnail from {video_path}")
        data = temp_file_path.read_bytes()
        temp_file_path.unlink()
        return data

    # Create a thumbnail from the first frame of the video
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(video_path)
        .output(temp_file_path, map="0:v:0", codec="mjpeg", vframes=1)
    )
    try:
        log.debug(f"Creating thumbnail from {video_path}")
        await ffmpeg.execute()
    except FFmpegError as e:
        log.exception(
            f"Unable to create thumbnail from {video_path}", exc_info=e, stack_info=True
        )
        log.debug(f"FFMPEG error: {e.message}")
        log.debug(f"Arguments to execute ffmpeg: {' '.join(e.arguments)}")
        return None

    data = temp_file_path.read_bytes()
    temp_file_path.unlink()
    return data
