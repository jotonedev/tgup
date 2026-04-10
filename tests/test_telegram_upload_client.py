import pytest
import asyncio
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

from telethon.tl import types, custom, functions
from telethon.errors import InvalidBufferError

from tgup.telegram_upload_client import TelegramUploadClient, PARALLEL_UPLOAD_BLOCKS


import pytest_asyncio

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
        client.client_call_mock = client._call # Reference to check calls
        
        return client

@pytest.mark.asyncio
async def test_get_maximum_file_size_bot(mock_client):
    mock_client.is_bot.return_value = True
    size = await mock_client.get_maximum_file_size()
    assert size == 50 * 1024 * 1024

@pytest.mark.asyncio
async def test_get_maximum_file_size_user_premium(mock_client):
    mock_client.is_bot.return_value = False
    class DummyUser:
        premium = True
    mock_client.get_me.return_value = DummyUser()
    size = await mock_client.get_maximum_file_size()
    assert size == 4 * 1024 * 1024 * 1024

@pytest.mark.asyncio
async def test_get_maximum_file_size_user_not_premium(mock_client):
    mock_client.is_bot.return_value = False
    class DummyUser:
        pass # missing attribute fallback to False
    mock_client.get_me.return_value = DummyUser()
    size = await mock_client.get_maximum_file_size()
    assert size == 2 * 1024 * 1024 * 1024

@pytest.mark.asyncio
async def test_decrease_upload_semaphore(mock_client):
    initial_blocks = PARALLEL_UPLOAD_BLOCKS
    assert mock_client.parallel_upload_blocks == initial_blocks
    
    # Needs a loop to run task
    mock_client.decrease_upload_semaphore()
    
    # Wait a bit for loop task to process
    await asyncio.sleep(0.01)
    
    assert mock_client.parallel_upload_blocks == initial_blocks - 1
    # Semaphore should have one less available
    # Since we can't easily check internal semaphore value in async,
    # we just trust the block logic ran and task was created.

@pytest.mark.asyncio
async def test_reconnect(mock_client):
    mock_client.is_connected.return_value = False
    await mock_client.reconnect()
    mock_client.connect.assert_called_once()
    
@pytest.mark.asyncio
async def test_reconnect_already_connected(mock_client):
    mock_client.is_connected.return_value = True
    await mock_client.reconnect()
    mock_client.connect.assert_not_called()

@pytest.mark.asyncio
async def test_upload_file_already_uploaded(mock_client):
    input_file = types.InputFile(123, 1, "test", b"")
    result = await mock_client.upload_file(input_file)
    assert result is input_file

@pytest.mark.asyncio
async def test_upload_file_invalid_part_size(mock_client):
    with patch("telethon.helpers._FileStream") as MockStream:
        mock_stream_context = MagicMock()
        mock_stream_context.file_size = 1000
        mock_stream_context.name = "dummy.txt"
        MockStream.return_value.__aenter__ = AsyncMock(return_value=mock_stream_context)
        MockStream.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="part size must be less or equal to 512KB"):
            await mock_client.upload_file("dummy.txt", part_size_kb=1024)
            
        with pytest.raises(ValueError, match="evenly divisible by 1024"):
            await mock_client.upload_file("dummy.txt", part_size_kb=511.5)

@pytest.mark.asyncio
async def test_upload_file_too_big(mock_client):
    mock_client.get_maximum_file_size = AsyncMock(return_value=10 * 1024 * 1024)
    with patch("telethon.helpers._FileStream") as MockStream:
        mock_stream_context = MagicMock()
        mock_stream_context.file_size = 20 * 1024 * 1024 # 20MB
        mock_stream_context.name = "dummy.txt"
        MockStream.return_value.__aenter__ = AsyncMock(return_value=mock_stream_context)
        MockStream.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="File too big"):
            await mock_client.upload_file("dummy.txt", part_size_kb=512)

@pytest.mark.asyncio
async def test_send_file_part_success(mock_client):
    request = MagicMock()
    progress_callback = MagicMock()
    
    mock_client.client_call_mock.return_value = True
    
    await mock_client._send_file_part(request, part_index=0, part_count=2, pos=1024, file_size=2048, progress_callback=progress_callback)
    
    mock_client.client_call_mock.assert_called_once_with(mock_client._sender, request, ordered=False)
    # the callback runs in another thread, we can't easily wait for it unless we hook into it
    # asyncio.to_thread makes it slightly tricky, but it should be called

@pytest.mark.asyncio
async def test_send_file_part_reconnect_on_error(mock_client):
    # Simulate first call returns connection error, second succeeds
    request = MagicMock()
    mock_client.client_call_mock.side_effect = [ConnectionError(), True]
    mock_client.reconnect = AsyncMock()
    
    # We may need to patch asyncio.sleep to not slow down tests
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await mock_client._send_file_part(request, part_index=0, part_count=1, pos=1024, file_size=1024)
    
    assert mock_client.client_call_mock.call_count == 2
    mock_client.reconnect.assert_called_once()
