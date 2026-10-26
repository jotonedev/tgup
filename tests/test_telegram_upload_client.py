import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from telethon.errors import InvalidBufferError
from telethon.errors.rpcerrorlist import FilePartsInvalidError
from telethon.tl import custom, types

from tgup.telegram_upload_client import (
    MAX_RECONNECT_RETRIES,
    PARALLEL_UPLOAD_BLOCKS,
    TelegramUploadClient,
)


@pytest_asyncio.fixture
async def mock_client():
    with patch("tgup.telegram_upload_client.TelegramClient.__init__", return_value=None):
        client = TelegramUploadClient("dummy_session", 12345, "dummy_hash")

        # Manually initialize attributes expected from TelegramUploadClient or TelegramClient
        client._log = MagicMock()
        client._sender = MagicMock()

        # Mock TelegramClient methods
        client.is_bot = AsyncMock()
        client.get_me = AsyncMock()
        client.connect = AsyncMock()
        client.is_connected = MagicMock(return_value=False)
        client._call = AsyncMock()
        client.client_call_mock = client._call  # Reference to check calls

        return client


@pytest.mark.parametrize(
    "is_bot,premium_attr,expected_size",
    [
        (True, None, 50 * 1024 * 1024),
        (False, True, 4 * 1024 * 1024 * 1024),
        (False, False, 2 * 1024 * 1024 * 1024),
        (False, "missing", 2 * 1024 * 1024 * 1024),
    ],
)
@pytest.mark.asyncio
async def test_get_maximum_file_size(mock_client, is_bot, premium_attr, expected_size):
    mock_client.is_bot.return_value = is_bot

    if not is_bot:

        class DummyUser:
            pass

        user = DummyUser()
        if premium_attr != "missing":
            user.premium = premium_attr
        mock_client.get_me.return_value = user

    size = await mock_client.get_maximum_file_size()
    assert size == expected_size


@pytest.mark.parametrize(
    "initial_blocks,expected_final_blocks,should_decrease",
    [
        (PARALLEL_UPLOAD_BLOCKS, PARALLEL_UPLOAD_BLOCKS - 1, True),
        (1, 1, False),
    ],
)
@pytest.mark.asyncio
async def test_decrease_upload_semaphore(
    mock_client, initial_blocks, expected_final_blocks, should_decrease
):
    mock_client.parallel_upload_blocks = initial_blocks
    mock_client.decrease_upload_semaphore()
    await asyncio.sleep(0.01)
    assert mock_client.parallel_upload_blocks == expected_final_blocks


@pytest.mark.parametrize(
    "is_connected,expect_connect_call",
    [
        (False, True),
        (True, False),
    ],
)
@pytest.mark.asyncio
async def test_reconnect(mock_client, is_connected, expect_connect_call):
    mock_client.is_connected.return_value = is_connected
    await mock_client.reconnect()
    if expect_connect_call:
        mock_client.connect.assert_called_once()
    else:
        mock_client.connect.assert_not_called()


@pytest.mark.asyncio
async def test_upload_file_already_uploaded(mock_client):
    input_file = types.InputFile(123, 1, "test", b"")
    result = await mock_client.upload_file(input_file)
    assert result is input_file


@pytest.mark.parametrize(
    "part_size_kb,error_match",
    [
        (1024, "part size must be less or equal to 512KB"),
        (511.5, "evenly divisible by 1024"),
    ],
)
@pytest.mark.asyncio
async def test_upload_file_invalid_part_size(mock_client, part_size_kb, error_match):
    with patch("telethon.helpers._FileStream") as MockStream:
        mock_stream_context = MagicMock()
        mock_stream_context.file_size = 1000
        mock_stream_context.name = "dummy.txt"
        MockStream.return_value.__aenter__ = AsyncMock(return_value=mock_stream_context)
        MockStream.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match=error_match):
            await mock_client.upload_file("dummy.txt", part_size_kb=part_size_kb)


@pytest.mark.asyncio
async def test_upload_file_too_big(mock_client):
    mock_client.get_maximum_file_size = AsyncMock(return_value=10 * 1024 * 1024)
    with patch("telethon.helpers._FileStream") as MockStream:
        mock_stream_context = MagicMock()
        mock_stream_context.file_size = 20 * 1024 * 1024  # 20MB
        mock_stream_context.name = "dummy.txt"
        MockStream.return_value.__aenter__ = AsyncMock(return_value=mock_stream_context)
        MockStream.return_value.__aexit__ = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="File too big"):
            await mock_client.upload_file("dummy.txt", part_size_kb=512)


@pytest.mark.parametrize(
    "file_size,custom_file_name,expected_type,expected_name",
    [
        (5 * 1024 * 1024, None, custom.InputSizedFile, "sample.txt"),
        (5 * 1024 * 1024, "custom.pdf", custom.InputSizedFile, "custom.pdf"),
        (15 * 1024 * 1024, None, types.InputFileBig, "sample.txt"),
        (15 * 1024 * 1024, "custom.mp4", types.InputFileBig, "custom.mp4"),
    ],
)
@pytest.mark.asyncio
async def test_upload_file_success_modes(
    mock_client, file_size, custom_file_name, expected_type, expected_name
):
    mock_client.get_maximum_file_size = AsyncMock(return_value=50 * 1024 * 1024)
    mock_client._send_file_part = AsyncMock()

    with patch("telethon.helpers._FileStream") as MockStream:
        mock_stream_context = MagicMock()
        mock_stream_context.file_size = file_size
        mock_stream_context.name = "sample.txt"
        # read chunks of 512KB
        mock_stream_context.read = AsyncMock(side_effect=lambda size: b"0" * size)

        MockStream.return_value.__aenter__ = AsyncMock(return_value=mock_stream_context)
        MockStream.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await mock_client.upload_file(
            "sample.txt",
            part_size_kb=512,
            file_name=custom_file_name,
        )

        assert isinstance(result, expected_type)
        assert result.name == expected_name


@pytest.mark.asyncio
async def test_send_file_part_success(mock_client):
    request = MagicMock()
    progress_callback = MagicMock()

    mock_client.client_call_mock.return_value = True

    await mock_client._send_file_part(
        request,
        part_index=0,
        part_count=2,
        pos=1024,
        file_size=2048,
        progress_callback=progress_callback,
    )

    mock_client.client_call_mock.assert_called_once_with(
        mock_client._sender, request, ordered=False
    )


@pytest.mark.parametrize(
    "initial_error,can_retry",
    [
        (ConnectionError(), True),
        (InvalidBufferError(b"1234"), True),
    ],
)
@pytest.mark.asyncio
async def test_send_file_part_reconnect_on_error(mock_client, initial_error, can_retry):
    if isinstance(initial_error, InvalidBufferError):
        initial_error.code = 429

    request = MagicMock()
    mock_client.client_call_mock.side_effect = [initial_error, True]
    mock_client.reconnect = AsyncMock()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await mock_client._send_file_part(
            request, part_index=0, part_count=1, pos=1024, file_size=1024
        )

    assert mock_client.client_call_mock.call_count == 2
    mock_client.reconnect.assert_called_once()


@pytest.mark.parametrize(
    "terminal_exception",
    [
        FilePartsInvalidError(None),
        InvalidBufferError(b"1234"),
    ],
)
@pytest.mark.asyncio
async def test_send_file_part_fatal_errors(mock_client, terminal_exception):
    if isinstance(terminal_exception, InvalidBufferError):
        terminal_exception.code = 500  # not 429

    request = MagicMock()
    mock_client.client_call_mock.side_effect = terminal_exception

    with pytest.raises(type(terminal_exception)):
        await mock_client._send_file_part(
            request, part_index=0, part_count=1, pos=1024, file_size=1024
        )


@pytest.mark.asyncio
async def test_send_file_part_max_retries_exceeded(mock_client):
    request = MagicMock()
    mock_client.client_call_mock.return_value = None

    with pytest.raises(RuntimeError, match="Failed to upload file part"):
        await mock_client._send_file_part(
            request,
            part_index=0,
            part_count=1,
            pos=1024,
            file_size=1024,
            retry=MAX_RECONNECT_RETRIES,
        )
