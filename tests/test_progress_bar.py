import io

import pytest

from tgup.progress_bar import DownloadProgressBar


@pytest.mark.parametrize(
    "updates,expected_total,expected_n",
    [
        ([(10, 100)], 100, 10),
        ([(10, 100), (35, 100), (100, 100)], 100, 100),
        ([(500, 1000), (750, 1500)], 1500, 750),
        ([(0, 50), (25, 50), (50, 50)], 50, 50),
        ([(1024, 2048), (2048, 2048)], 2048, 2048),
    ],
)
def test_download_progress_bar_update_to(updates, expected_total, expected_n):
    buffer = io.StringIO()
    pg = DownloadProgressBar(file=buffer)
    try:
        for current, total in updates:
            pg.update_to(current, total)
        assert pg.total == expected_total
        assert pg.n == expected_n
    finally:
        pg.close()


@pytest.mark.parametrize(
    "initial_kwargs",
    [
        {"unit": "B", "unit_scale": True},
        {"desc": "uploading.mp4", "dynamic_ncols": True},
        {"smoothing": 0.2, "mininterval": 0.5},
    ],
)
def test_download_progress_bar_init_options(initial_kwargs):
    buffer = io.StringIO()
    pg = DownloadProgressBar(file=buffer, **initial_kwargs)
    try:
        assert isinstance(pg, DownloadProgressBar)
    finally:
        pg.close()


@pytest.mark.parametrize(
    "desc,expected_desc",
    [
        ("short_title.mp4", "short_title.mp4"),
        ("a" * 32, "a" * 32),
        ("a" * 50, "a" * 32),
    ],
)
def test_download_progress_bar_desc_truncation(desc, expected_desc):
    buffer = io.StringIO()
    pg = DownloadProgressBar(file=buffer, desc=desc)
    try:
        assert pg.desc == expected_desc
    finally:
        pg.close()


def test_download_progress_bar_desc_positional():
    buffer = io.StringIO()
    pg = DownloadProgressBar(None, "a" * 50, file=buffer)
    try:
        assert pg.desc == "a" * 32
    finally:
        pg.close()
