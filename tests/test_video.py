from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ffmpeg import FFmpegError

from tgup.video import extract_thumbnail, get_mime_type, is_video_mp4, is_video_type


@pytest.mark.parametrize(
    "filename,expected_mime_prefix",
    [
        ("video.mp4", "video/mp4"),
        ("video.webm", "video/webm"),
        ("photo.jpg", "image/jpeg"),
        ("photo.jpeg", "image/jpeg"),
        ("photo.png", "image/png"),
        ("document.txt", "text/plain"),
        ("archive.zip", "application/"),
        ("no_extension", ""),
        ("unknown.xyz123", ""),
    ],
)
def test_get_mime_type_various_extensions(filename, expected_mime_prefix):
    path = Path(filename)
    mime = get_mime_type(path)
    assert mime.startswith(expected_mime_prefix)


@pytest.mark.parametrize(
    "filename,expected_is_video",
    [
        ("sample.mp4", True),
        ("sample.mkv", True),
        ("sample.avi", True),
        ("sample.mov", True),
        ("sample.webm", True),
        ("sample.txt", False),
        ("sample.zip", False),
        ("sample.pdf", False),
        ("sample.jpg", False),
        ("sample", False),
    ],
)
def test_is_video_type(filename, expected_is_video):
    assert is_video_type(Path(filename)) is expected_is_video


@pytest.mark.parametrize(
    "filename,expected_is_mp4",
    [
        ("sample.mp4", True),
        ("sample.MP4", True),
        ("sample.txt", False),
    ],
)
def test_is_video_mp4(filename, expected_is_mp4):
    assert is_video_mp4(Path(filename)) is expected_is_mp4


@pytest.mark.asyncio
async def test_extract_thumbnail_not_found(tmp_path):
    missing_file = tmp_path / "not_found.mp4"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        await extract_thumbnail(missing_file)


@pytest.mark.parametrize(
    "attached_pic_error,first_frame_error,expected_result",
    [
        (None, None, b"attached_pic_bytes"),
        (FFmpegError("no pic", ["ffmpeg"]), None, b"first_frame_bytes"),
        (
            FFmpegError("no pic", ["ffmpeg"]),
            FFmpegError("corrupt video", ["ffmpeg"]),
            None,
        ),
    ],
)
@pytest.mark.asyncio
async def test_extract_thumbnail_scenarios(
    tmp_path, attached_pic_error, first_frame_error, expected_result
):
    video_path = tmp_path / "test.mp4"
    video_path.write_bytes(b"dummy_video_content")

    def make_ffmpeg_builder(temp_file_bytes):
        mock_instance = MagicMock()
        mock_instance.option.return_value = mock_instance
        mock_instance.input.return_value = mock_instance

        temp_target = []

        def mock_output(path, **kwargs):
            temp_target.append(Path(path))
            return mock_instance

        mock_instance.output.side_effect = mock_output

        async def mock_execute():
            if temp_target and temp_file_bytes is not None:
                temp_target[-1].write_bytes(temp_file_bytes)

        mock_instance.execute = AsyncMock(side_effect=mock_execute)
        return mock_instance

    ffmpeg_instance_1 = make_ffmpeg_builder(b"attached_pic_bytes")
    if attached_pic_error:
        ffmpeg_instance_1.execute = AsyncMock(side_effect=attached_pic_error)

    ffmpeg_instance_2 = make_ffmpeg_builder(b"first_frame_bytes")
    if first_frame_error:
        ffmpeg_instance_2.execute = AsyncMock(side_effect=first_frame_error)

    with patch("tgup.video.FFmpeg", side_effect=[ffmpeg_instance_1, ffmpeg_instance_2]):
        result = await extract_thumbnail(video_path)

    assert result == expected_result
