import argparse
import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient
from telethon.hints import EntityLike

from tgup.client import TgupClient
from tgup.progress_bar import DownloadProgressBar
from tgup.utils import list_files, setup_logging
from tgup.video import extract_thumbnail, is_video_type, is_video_mp4


__all__ = ["upload_file", "run", "main"]


log = logging.getLogger(__name__)


async def upload_file(
    file_path: Path,
    client: TelegramClient,
    to_chat: EntityLike,
    no_thumbnail: bool = False,
    thumbnail: bytes | None = None,
):
    # Parse thumbnail options
    if is_video_type(file_path):
        if not no_thumbnail and thumbnail is None:
            thumbnail = await extract_thumbnail(file_path)
        elif no_thumbnail:
            thumbnail = None
    else:
        thumbnail = None

    log.info(f"Uploading {file_path}")

    # Create a progress bar
    pg = DownloadProgressBar(unit="B", unit_scale=True, miniters=1, desc=file_path.name)

    # Get file size
    file_size = file_path.stat().st_size

    # Upload the file
    await client.send_file(
        to_chat,
        str(file_path),
        caption=file_path.stem,
        thumb=thumbnail,
        supports_streaming=is_video_mp4(file_path),
        progress_callback=pg.update_to,
        file_size=file_size,
    )
    # Stop progress bar
    pg.close()
    log.info(f"Uploaded {file_path}")


async def run(
    nodes: list[Path],
    recursively: bool,
    no_thumbnail: bool,
    thumbnail_file: Path | None,
):
    # Set-up client
    client = TgupClient()

    # Start client and login if necessary
    await client.login_interactive()

    # Parse thumbnail
    if no_thumbnail:
        thumbnail = None
    else:
        if isinstance(thumbnail_file, Path):
            with open(thumbnail_file, "rb") as f:
                thumbnail = f.read()
        else:
            thumbnail = None

    # Get the personal chat
    to_chat = await client.get_input_entity("me")

    # Upload files
    for node in nodes:
        files = list_files(node, recursively=recursively)
        for file in files:
            await upload_file(
                file,
                client,
                to_chat,
                thumbnail=thumbnail,
                no_thumbnail=no_thumbnail,
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", help="Files to upload")
    parser.add_argument(
        "--recursively",
        action="store_true",
        help="Recursively list files",
        default=False,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--no-thumbnail",
        action="store_true",
        default=False,
        help="Disable thumbnail generation. Telegram may generate one for some known formats.",
    )
    group.add_argument(
        "--thumbnail-file",
        default=None,
        type=Path,
        help="Path to the preview file to use for the uploaded file.",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging level
    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    setup_logging(level)

    try:
        asyncio.run(
            run(args.files, args.recursively, args.no_thumbnail, args.thumbnail_file)
        )
    except KeyboardInterrupt:
        log.info("Interrupted. Exiting.")


if __name__ == "__main__":
    main()
