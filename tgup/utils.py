import logging
import re
from pathlib import Path
from os import cpu_count

__all__ = ["list_files", "phone_match", "setup_logging", "cpu_count"]


def setup_logging(level: int = logging.INFO):
    # set visualization
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    telethon_logger = logging.getLogger("telethon")
    telethon_logger.setLevel(logging.WARNING)


def list_files(directory: Path, *, recursively: bool = False) -> set[Path]:
    """
    List all files in a directory.
    Args:
        directory: Path to the directory.
        recursively: Whether to list files recursively.

    Returns:
        Set of file paths.
    """
    if not isinstance(directory, Path):
        directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory {directory} does not exist.")
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory.")

    files = set()
    if recursively:
        for node in directory.rglob("*"):
            if node.is_file():
                files.add(node.resolve())
    else:
        for node in directory.glob("*"):
            if node.is_file():
                files.add(node.resolve())

    return files


def phone_match(value: str):
    """
    Validate whether the given string is a valid phone number.

    Args:
        value (str): The phone number string to validate.
                     The string may optionally include a '+' sign,
                     digits, dots, spaces, parentheses, or dashes.

    Returns:
        str: The input phone number string, if it is valid.

    Raises:
        ValueError: If the input string does not match the expected phone number format.
    """
    match = re.match(r"\+?[0-9.()\[\] \-]+", value)
    if match is None:
        raise ValueError("{} is not a valid phone".format(value))
    return value


def get_number_threads() -> int:
    """
    Returns:
        int: The number of threads available to the Python interpreter.
    """
    return cpu_count()
