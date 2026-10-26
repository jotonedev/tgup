import importlib
from pathlib import Path

import pytest

import tgup.config


@pytest.mark.parametrize(
    "env_value,expected_dir_name",
    [
        (None, ".config"),
        ("/custom/config/dir", "dir"),
        ("~/custom_config", "custom_config"),
    ],
)
def test_config_paths_with_env(monkeypatch, env_value, expected_dir_name):
    if env_value is None:
        monkeypatch.delenv("TELEGRAM_UPLOAD_CONFIG_DIRECTORY", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_UPLOAD_CONFIG_DIRECTORY", env_value)

    reloaded_config = importlib.reload(tgup.config)

    assert reloaded_config.CONFIG_FILE.name == "telegram-upload.json"
    assert reloaded_config.SESSION_FILE.name == "telegram-upload"
    assert reloaded_config.CONFIG_FILE.parent == reloaded_config.CONFIG_DIRECTORY.expanduser()
    assert reloaded_config.SESSION_FILE.parent == reloaded_config.CONFIG_DIRECTORY.expanduser()
    assert reloaded_config.CONFIG_DIRECTORY.expanduser().name == expected_dir_name
    assert isinstance(reloaded_config.CONFIG_DIRECTORY, Path)
