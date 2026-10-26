from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tgup.upload import main, run, upload_file


@pytest.mark.parametrize(
    "file_name,is_video,is_mp4,no_thumbnail,thumb_input,extract_return,extract_raises,expected_thumb,expected_streaming",
    [
        # MP4 video without thumbnail input -> extracts thumbnail
        ("video.mp4", True, True, False, None, b"extracted_thumb", None, b"extracted_thumb", True),
        # MP4 video with no_thumbnail flag -> None
        ("video.mp4", True, True, True, None, b"extracted_thumb", None, None, True),
        # MP4 video with custom thumbnail provided -> uses custom
        ("video.mp4", True, True, False, b"custom_thumb", None, None, b"custom_thumb", True),
        # MKV video without thumbnail -> extracts thumbnail, supports_streaming is False
        (
            "video.mkv",
            True,
            False,
            False,
            None,
            b"extracted_thumb",
            None,
            b"extracted_thumb",
            False,
        ),
        # Video when ffmpeg is missing (FileNotFoundError) -> thumbnail is None
        (
            "video.mp4",
            True,
            True,
            False,
            None,
            None,
            FileNotFoundError("ffmpeg missing"),
            None,
            True,
        ),
        # Non-video file -> thumbnail is None, supports_streaming is False
        ("doc.pdf", False, False, False, None, None, None, None, False),
        # Non-video file even if thumb passed -> thumbnail is None
        ("doc.pdf", False, False, False, b"thumb", None, None, None, False),
    ],
)
@pytest.mark.asyncio
async def test_upload_file(
    tmp_path,
    file_name,
    is_video,
    is_mp4,
    no_thumbnail,
    thumb_input,
    extract_return,
    extract_raises,
    expected_thumb,
    expected_streaming,
):
    test_file = tmp_path / file_name
    test_file.write_bytes(b"dummy_content_bytes")

    client = MagicMock()
    client.send_file = AsyncMock()

    to_chat = "test_chat"

    with (
        patch("tgup.upload.is_video_type", return_value=is_video),
        patch("tgup.upload.is_video_mp4", return_value=is_mp4),
        patch("tgup.upload.extract_thumbnail") as mock_extract,
        patch("tgup.upload.DownloadProgressBar") as mock_pg_cls,
    ):
        mock_pg = MagicMock()
        mock_pg_cls.return_value = mock_pg

        if extract_raises:
            mock_extract.side_effect = extract_raises
        else:
            mock_extract.return_value = extract_return

        await upload_file(
            file_path=test_file,
            client=client,
            to_chat=to_chat,
            no_thumbnail=no_thumbnail,
            thumbnail=thumb_input,
        )

        client.send_file.assert_called_once_with(
            to_chat,
            str(test_file),
            caption=test_file.stem,
            thumb=expected_thumb,
            supports_streaming=expected_streaming,
            progress_callback=mock_pg.update_to,
            file_size=len(b"dummy_content_bytes"),
        )
        mock_pg_cls.assert_called_once_with(
            unit="B",
            unit_scale=True,
            desc=test_file.name[:32],
            dynamic_ncols=True,
            smoothing=0.2,
            mininterval=0.5,
            miniters=1,
        )
        mock_pg.close.assert_called_once()


@pytest.mark.parametrize(
    "filename,expected_desc",
    [
        ("short.mp4", "short.mp4"),
        ("a" * 32, "a" * 32),
        ("a" * 50 + ".txt", ("a" * 50 + ".txt")[:32]),
    ],
)
@pytest.mark.asyncio
async def test_upload_file_desc_truncation(tmp_path, filename, expected_desc):
    test_file = tmp_path / filename
    test_file.write_text("dummy")

    client = MagicMock()
    client.send_file = AsyncMock()

    with patch("tgup.upload.DownloadProgressBar") as mock_pg_cls:
        mock_pg = MagicMock()
        mock_pg_cls.return_value = mock_pg

        await upload_file(test_file, client, "me")

        mock_pg_cls.assert_called_once()
        _, kwargs = mock_pg_cls.call_args
        assert kwargs["desc"] == expected_desc
        assert len(kwargs["desc"]) <= 32


@pytest.mark.parametrize(
    "to_arg,expected_entity",
    [
        ("me", "me"),
        ("@mychannel", "@mychannel"),
        ("123456789", 123456789),
        ("-1001234567890", -1001234567890),
    ],
)
@pytest.mark.parametrize("recursively", [False, True])
@pytest.mark.asyncio
async def test_run_success(tmp_path, to_arg, expected_entity, recursively):
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello")

    with (
        patch("tgup.upload.TgupClient") as mock_client_cls,
        patch("tgup.upload.upload_file", new_callable=AsyncMock) as mock_upload_file,
    ):
        client_instance = MagicMock()
        client_instance.login_interactive = AsyncMock()
        client_instance.get_input_entity = AsyncMock(return_value="resolved_entity")
        mock_client_cls.return_value = client_instance

        await run(
            nodes=[tmp_path],
            recursively=recursively,
            no_thumbnail=False,
            thumbnail_file=None,
            to=to_arg,
        )

        client_instance.login_interactive.assert_called_once()
        client_instance.get_input_entity.assert_called_once_with(expected_entity)
        mock_upload_file.assert_called_once_with(
            f1.resolve(),
            client_instance,
            "resolved_entity",
            thumbnail=None,
            no_thumbnail=False,
        )


@pytest.mark.parametrize(
    "no_thumbnail,thumb_path_exists,expected_thumb",
    [
        (True, True, None),
        (False, True, b"thumbnail_bytes"),
        (False, False, None),
    ],
)
@pytest.mark.asyncio
async def test_run_thumbnail_handling(tmp_path, no_thumbnail, thumb_path_exists, expected_thumb):
    f1 = tmp_path / "file.mp4"
    f1.write_text("content")

    if thumb_path_exists:
        thumb_file = tmp_path / "thumb.jpg"
        thumb_file.write_bytes(b"thumbnail_bytes")
    else:
        thumb_file = None

    with (
        patch("tgup.upload.TgupClient") as mock_client_cls,
        patch("tgup.upload.upload_file", new_callable=AsyncMock) as mock_upload_file,
    ):
        client_instance = MagicMock()
        client_instance.login_interactive = AsyncMock()
        client_instance.get_input_entity = AsyncMock(return_value="chat_entity")
        mock_client_cls.return_value = client_instance

        await run(
            nodes=[f1],
            recursively=False,
            no_thumbnail=no_thumbnail,
            thumbnail_file=thumb_file,
            to="me",
        )

        mock_upload_file.assert_called_once_with(
            f1.resolve(),
            client_instance,
            "chat_entity",
            thumbnail=expected_thumb,
            no_thumbnail=no_thumbnail,
        )


@pytest.mark.asyncio
async def test_run_unknown_entity():
    with (
        patch("tgup.upload.TgupClient") as mock_client_cls,
        patch("tgup.upload.upload_file", new_callable=AsyncMock) as mock_upload_file,
    ):
        client_instance = MagicMock()
        client_instance.login_interactive = AsyncMock()
        client_instance.get_input_entity = AsyncMock(side_effect=ValueError("Unknown entity"))
        mock_client_cls.return_value = client_instance

        await run(
            nodes=[Path("some_file.txt")],
            recursively=False,
            no_thumbnail=False,
            thumbnail_file=None,
            to="non_existent",
        )

        client_instance.get_input_entity.assert_called_once_with("non_existent")
        mock_upload_file.assert_not_called()


@pytest.mark.asyncio
async def test_run_upload_file_value_error(tmp_path):
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"
    f1.write_text("1")
    f2.write_text("2")

    with (
        patch("tgup.upload.TgupClient") as mock_client_cls,
        patch("tgup.upload.upload_file", new_callable=AsyncMock) as mock_upload_file,
    ):
        client_instance = MagicMock()
        client_instance.login_interactive = AsyncMock()
        client_instance.get_input_entity = AsyncMock(return_value="resolved_chat")
        mock_client_cls.return_value = client_instance

        # First upload fails with ValueError, second succeeds
        mock_upload_file.side_effect = [ValueError("Upload error"), None]

        await run(
            nodes=[tmp_path],
            recursively=False,
            no_thumbnail=False,
            thumbnail_file=None,
            to="me",
        )

        assert mock_upload_file.call_count == 2


@pytest.mark.parametrize(
    "cli_args,expected_files,expected_recursively,expected_to,expected_no_thumb,expected_thumb_file,expected_debug",
    [
        (["file.mp4"], ["file.mp4"], False, "me", False, None, False),
        (
            ["file1.txt", "file2.txt", "--recursively"],
            ["file1.txt", "file2.txt"],
            True,
            "me",
            False,
            None,
            False,
        ),
        (
            ["file.mp4", "--to", "@target_channel"],
            ["file.mp4"],
            False,
            "@target_channel",
            False,
            None,
            False,
        ),
        (["file.mp4", "--no-thumbnail"], ["file.mp4"], False, "me", True, None, False),
        (
            ["file.mp4", "--thumbnail-file", "thumb.jpg"],
            ["file.mp4"],
            False,
            "me",
            False,
            Path("thumb.jpg"),
            False,
        ),
        (["file.mp4", "--debug"], ["file.mp4"], False, "me", False, None, True),
    ],
)
def test_main_cli_args(
    cli_args,
    expected_files,
    expected_recursively,
    expected_to,
    expected_no_thumb,
    expected_thumb_file,
    expected_debug,
):
    with (
        patch("sys.argv", ["tgup"] + cli_args),
        patch("tgup.upload.asyncio.run") as mock_async_run,
        patch("tgup.upload.setup_logging") as mock_setup_logging,
        patch("tgup.upload.run") as mock_run,
    ):
        mock_async_run.side_effect = lambda coro: coro.close()
        main()

        expected_level = 10 if expected_debug else 30  # DEBUG=10, WARNING=30
        mock_setup_logging.assert_called_once_with(expected_level)
        mock_async_run.assert_called_once()
        mock_run.assert_called_once_with(
            expected_files,
            expected_recursively,
            expected_no_thumb,
            expected_thumb_file,
            expected_to,
        )


def test_main_cli_mutually_exclusive_thumbnail_options():
    with (
        patch("sys.argv", ["tgup", "file.mp4", "--no-thumbnail", "--thumbnail-file", "t.jpg"]),
        pytest.raises(SystemExit),
    ):
        main()


def test_main_keyboard_interrupt():
    def raise_interrupt(coro):
        coro.close()
        raise KeyboardInterrupt

    with (
        patch("sys.argv", ["tgup", "file.mp4"]),
        patch("tgup.upload.asyncio.run", side_effect=raise_interrupt),
        patch("tgup.upload.log.info") as mock_log_info,
    ):
        main()
        mock_log_info.assert_called_with("Interrupted. Exiting.")
