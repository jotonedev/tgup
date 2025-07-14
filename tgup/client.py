import json
from getpass import getpass
from pathlib import Path


from .config import SESSION_FILE, CONFIG_FILE
from .telegram_upload_client import TelegramUploadClient
from .utils import phone_match


def input_phone():
    """
    Get phone number from user input and validate it.

    Returns:
        str: Validated phone number.

    Raises:
        ValueError: If the phone number is invalid.
    """
    phone = input("Enter your phone number: ")
    return phone_match(phone)


def input_password():
    """
    Get the password from user input securely.

    Returns:
        str: The entered password.
    """
    return getpass("Enter your password: ")


class TgupClient(TelegramUploadClient):
    def __init__(self, config_file: Path = CONFIG_FILE, proxy=None, **kwargs):
        if isinstance(config_file, Path):
            config_file = config_file.resolve()
        else:
            raise TypeError("config_file must be a Path object.")

        if not config_file.exists():
            api_id, api_hash = self.setup_interactive()
            config = {
                "api_id": api_id,
                "api_hash": api_hash,
            }
            config_file.write_text(json.dumps(config))
        else:
            with open(config_file) as f:
                config = json.load(f)

        self._config_file = config_file
        # noinspection PyUnboundLocalVariable
        super().__init__(
            config.get("session", SESSION_FILE),
            config["api_id"],
            config["api_hash"],
            proxy=proxy,
            **kwargs,
        )

    @staticmethod
    def setup_interactive() -> tuple[str, str]:
        """Ask for information from https://my.telegram.org"""
        api_id = input("Enter API ID: ")
        api_hash = input("Enter API hash: ")
        return api_id, api_hash

    async def login_interactive(
        self,
        bot_token=None,
        force_sms=False,
        first_name="New User",
        last_name="",
        max_attempts=3,
    ):
        # noinspection PyUnresolvedReferences
        return await self.start(
            phone=input_phone,
            password=input_password,
            bot_token=bot_token,
            force_sms=force_sms,
            first_name=first_name,
            last_name=last_name,
            max_attempts=max_attempts,
        )
