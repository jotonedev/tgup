import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from tgup.utils import get_number_threads, list_files, phone_match, setup_logging


@pytest.mark.parametrize(
    "phone_input,expected_output",
    [
        ("+1234567890", "+1234567890"),
        ("1234567890", "1234567890"),
        ("+1 (800) 555-0199", "+1 (800) 555-0199"),
        ("123-456-7890", "123-456-7890"),
        ("123.456.7890", "123.456.7890"),
        ("[123] 456-7890", "[123] 456-7890"),
        ("+33 6 12 34 56 78", "+33 6 12 34 56 78"),
        ("+44-20-7946-0958", "+44-20-7946-0958"),
        ("001 555 1234", "001 555 1234"),
    ],
)
def test_phone_match_valid(phone_input, expected_output):
    assert phone_match(phone_input) == expected_output


@pytest.mark.parametrize(
    "invalid_phone",
    [
        "invalid",
        "abc123",
        "@12345",
        "phone",
        "",
        "!@#$%^&*",
        "?+12345",
    ],
)
def test_phone_match_invalid(invalid_phone):
    with pytest.raises(ValueError, match="is not a valid phone"):
        phone_match(invalid_phone)


@pytest.mark.parametrize(
    "recursively,expected_file_names",
    [
        (False, {"root_file1.txt", "root_file2.txt"}),
        (True, {"root_file1.txt", "root_file2.txt", "sub_file1.txt", "deep_file.txt"}),
    ],
)
def test_list_files_directory(tmp_path, recursively, expected_file_names):
    # Setup files
    (tmp_path / "root_file1.txt").write_text("1")
    (tmp_path / "root_file2.txt").write_text("2")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "sub_file1.txt").write_text("3")

    deepdir = subdir / "deep"
    deepdir.mkdir()
    (deepdir / "deep_file.txt").write_text("4")

    files = list_files(tmp_path, recursively=recursively)
    assert {f.name for f in files} == expected_file_names
    assert all(isinstance(f, Path) for f in files)


@pytest.mark.parametrize("use_str_path", [False, True])
@pytest.mark.parametrize("recursively", [False, True])
def test_list_files_single_file(tmp_path, use_str_path, recursively):
    test_file = tmp_path / "single.txt"
    test_file.write_text("content")

    arg = str(test_file) if use_str_path else test_file
    files = list_files(arg, recursively=recursively)
    assert files == {test_file.resolve()}


def test_list_files_empty_directory(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert list_files(empty_dir) == set()
    assert list_files(empty_dir, recursively=True) == set()


def test_list_files_not_found(tmp_path):
    non_existent = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        list_files(non_existent)


@pytest.mark.parametrize(
    "log_level",
    [
        logging.DEBUG,
        logging.ERROR,
    ],
)
def test_setup_logging(log_level):
    with patch("logging.basicConfig") as mock_basic_config:
        setup_logging(log_level)
        mock_basic_config.assert_called_once_with(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    assert logging.getLogger("telethon").level == logging.WARNING


@pytest.mark.parametrize(
    "mock_cpus,expected_threads",
    [
        (1, 1),
        (16, 16)
    ],
)
def test_get_number_threads(mock_cpus, expected_threads):
    with patch("tgup.utils.cpu_count", return_value=mock_cpus):
        assert get_number_threads() == expected_threads
