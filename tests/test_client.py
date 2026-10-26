import json
from unittest.mock import AsyncMock, patch

import pytest

from tgup.client import TgupClient, input_password, input_phone
from tgup.config import SESSION_FILE


@pytest.mark.parametrize(
    "user_input,expected",
    [
        ("+1234567890", "+1234567890"),
        ("123456789", "123456789"),
        ("+33 6 12 34 56 78", "+33 6 12 34 56 78"),
    ],
)
def test_input_phone_valid(user_input, expected):
    with patch("builtins.input", return_value=user_input):
        assert input_phone() == expected


@pytest.mark.parametrize(
    "invalid_input",
    [
        "invalid_phone",
        "abc",
        "",
        "@phone",
    ],
)
def test_input_phone_invalid(invalid_input):
    with (
        patch("builtins.input", return_value=invalid_input),
        pytest.raises(ValueError, match="is not a valid phone"),
    ):
        input_phone()


@pytest.mark.parametrize(
    "password_input",
    [
        "secret_password",
        "p@ssw0rd!#123",
        "",
    ],
)
def test_input_password(password_input):
    with patch("tgup.client.getpass", return_value=password_input):
        assert input_password() == password_input


@pytest.mark.parametrize(
    "invalid_config_file",
    [
        "string_path_not_path_object",
        12345,
        None,
        ["path/to/file"],
        {"path": "file"},
    ],
)
def test_tgup_client_init_invalid_type(invalid_config_file):
    with pytest.raises(TypeError, match="config_file must be a Path object"):
        TgupClient(config_file=invalid_config_file)


@pytest.mark.parametrize(
    "config_content,expected_session",
    [
        ({"api_id": 111, "api_hash": "hash111"}, SESSION_FILE),
        ({"api_id": 222, "api_hash": "hash222", "session": "custom_session"}, "custom_session"),
    ],
)
@pytest.mark.parametrize("proxy", [None, ("socks5", "127.0.0.1", 1080)])
def test_tgup_client_init_existing_config(tmp_path, config_content, expected_session, proxy):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_content))

    with patch("tgup.client.TelegramUploadClient.__init__", return_value=None) as mock_super_init:
        client = TgupClient(config_file=config_file, proxy=proxy, test_kwarg="value")

        assert client._config_file == config_file.resolve()
        mock_super_init.assert_called_once_with(
            expected_session,
            config_content["api_id"],
            config_content["api_hash"],
            proxy=proxy,
            test_kwarg="value",
        )


@pytest.mark.parametrize(
    "interactive_inputs",
    [
        ("12345", "hash_interactive_1"),
        ("98765", "hash_interactive_2"),
    ],
)
def test_tgup_client_init_non_existing_config(tmp_path, interactive_inputs):
    config_file = tmp_path / "subfolder" / "new_config.json"
    assert not config_file.exists()

    with (
        patch.object(
            TgupClient, "setup_interactive", return_value=interactive_inputs
        ) as mock_setup,
        patch("tgup.client.TelegramUploadClient.__init__", return_value=None) as mock_super_init,
    ):
        client = TgupClient(config_file=config_file)

        assert config_file.exists()
        saved_data = json.loads(config_file.read_text())
        assert saved_data["api_id"] == interactive_inputs[0]
        assert saved_data["api_hash"] == interactive_inputs[1]

        mock_setup.assert_called_once()
        mock_super_init.assert_called_once_with(
            SESSION_FILE,
            interactive_inputs[0],
            interactive_inputs[1],
            proxy=None,
        )
        assert client._config_file == config_file.resolve()


@pytest.mark.parametrize(
    "api_id_in,api_hash_in",
    [
        ("99999", "secret_hash"),
        ("11111", "another_hash"),
    ],
)
def test_tgup_client_setup_interactive(api_id_in, api_hash_in):
    with patch("builtins.input", side_effect=[api_id_in, api_hash_in]):
        api_id, api_hash = TgupClient.setup_interactive()
        assert api_id == api_id_in
        assert api_hash == api_hash_in


@pytest.mark.parametrize(
    "login_kwargs",
    [
        {},
        {"bot_token": "token123"},
        {"force_sms": True, "max_attempts": 5},
        {"first_name": "Alice", "last_name": "Bob", "max_attempts": 2},
    ],
)
@pytest.mark.asyncio
async def test_tgup_client_login_interactive(tmp_path, login_kwargs):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"api_id": 123, "api_hash": "hash"}))

    with patch("tgup.client.TelegramUploadClient.__init__", return_value=None):
        client = TgupClient(config_file=config_file)
        client.start = AsyncMock(return_value="login_successful")

        result = await client.login_interactive(**login_kwargs)
        assert result == "login_successful"

        expected_call_kwargs = {
            "phone": input_phone,
            "password": input_password,
            "bot_token": login_kwargs.get("bot_token", None),
            "force_sms": login_kwargs.get("force_sms", False),
            "first_name": login_kwargs.get("first_name", "New User"),
            "last_name": login_kwargs.get("last_name", ""),
            "max_attempts": login_kwargs.get("max_attempts", 3),
        }
        client.start.assert_called_once_with(**expected_call_kwargs)
