import logging
import time

from pyrogram.types import Chat, Message, User
from telegraph.aio import Telegraph

from .media_helper import bytes_to_mb
from ..config import Config

TELEGRAPH: None | Telegraph = None

PROGRESS_DICT = {}

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


async def post_to_telegraph(title: str, text: str) -> str:
    telegraph = await TELEGRAPH.create_page(
        title=title,
        html_content=f"<p>{text}</p>",
        author_name=Config.BOT_NAME,
        author_url=Config.UPSTREAM_REPO,
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


async def progress(
    current: int,
    total: int,
    response: Message | None = None,
    action: str = "",
    file_name: str = "",
    file_path: str = "",
):
    if not response:
        return
    if current == total:
        PROGRESS_DICT.pop(file_path, "")
        return
    current_time = time.time()
    if file_path not in PROGRESS_DICT or (current_time - PROGRESS_DICT[file_path]) > 5:
        PROGRESS_DICT[file_path] = current_time
        if total:
            percentage = round((current * 100 / total), 1)
        else:
            percentage = 0
        await response.edit(
            f"<b>{action}</b>"
            f"\n<pre language=bash>"
            f"\nfile={file_name}"
            f"\npath={file_path}"
            f"\nsize={bytes_to_mb(total)}mb"
            f"\ncompleted={bytes_to_mb(current)}mb | {percentage}%</pre>"
        )
