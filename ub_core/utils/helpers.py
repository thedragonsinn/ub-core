import logging
import time
from collections import defaultdict
from typing import Any

from pyrogram.enums import ParseMode
from pyrogram.types import Chat, Message, User
from telegraph.aio import Telegraph

from .media_helper import bytes_to_mb
from ..config import Config

TELEGRAPH: None | Telegraph = None


PROGRESS_DICT: dict[str, dict[str, float]] = defaultdict(
    lambda: {"start_time": (t := time.time()), "progress_time": t}
)

LOGGER = logging.getLogger(Config.BOT_NAME)


async def init_task():
    global TELEGRAPH
    TELEGRAPH = Telegraph()
    try:
        await TELEGRAPH.create_account(
            short_name=Config.BOT_NAME,
            author_name=Config.BOT_NAME,
            author_url=Config.UPSTREAM_REPO,
        )
    except Exception:
        LOGGER.error("Failed to Create Telegraph Account.")


async def post_to_telegraph(
    title: str,
    text: str,
    author_name: str = Config.BOT_NAME,
    author_url: str = Config.UPSTREAM_REPO,
) -> str:
    telegraph = await TELEGRAPH.create_page(
        title=title,
        html_content=f"<p>{text}</p>",
        author_name=author_name,
        author_url=author_url,
    )
    return telegraph["url"]


def get_name(user_or_chat: User | Chat) -> str:
    first = user_or_chat.first_name or ""
    last = user_or_chat.last_name or ""
    name = f"{first} {last}".strip()
    if not name:
        name = user_or_chat.title
    return name


def extract_user_data(user: User) -> dict:
    return dict(name=get_name(user), username=user.username, mention=user.mention)


def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}m {seconds}s"


async def progress(
    current_size: int,
    total_size: int,
    response: Message,
    action_str: str = "",
    file_path: str = "",
):
    if current_size == total_size:
        PROGRESS_DICT.pop(file_path, 0)
        return

    # start and progress time
    progress_info = PROGRESS_DICT[file_path]

    current_time = time.time()

    # if it has not been 8 sec since the last edit don't show progress.
    edit_time_diff = current_time - progress_info["progress_time"]
    if edit_time_diff < 8:
        return

    # Update progress time to current time
    progress_info["progress_time"] = current_time

    # Time Since Download/Upload started
    elapsed_time = current_time - progress_info["start_time"]

    # Progress %
    percentage = (current_size / total_size) * 100

    # Speed
    speed = current_size / elapsed_time

    # Remaining time till task completes.
    remaining_time = 0
    if speed:
        remaining_time = format_time((total_size - current_size) / speed)

    # Indicator [#---]
    bar_length = 15
    fill_length = (current_size / total_size) * bar_length
    progress_bar = "[" + ("#" * int(fill_length)).ljust(bar_length, "-") + "]"

    await response.edit(
        text=f"""
<b>{action_str.capitalize()}</b> <code>{percentage:.2f}%</code>

<code>{file_path}</code>

<code>{progress_bar}</code> | <code>{bytes_to_mb(current_size)}</code>/<code>{bytes_to_mb(total_size)}</code>MB

️Time remaining: <code>{remaining_time}</code>
""",
        parse_mode=ParseMode.HTML,
    )


def create_chunks(array: list[Any], chunk_size: int = 5) -> list[list[Any]]:
    """
    Split an Iterable into chunks.
    Defaults to chunks of 5
    """
    return [array[idx : idx + chunk_size] for idx in range(0, len(array), chunk_size)]
