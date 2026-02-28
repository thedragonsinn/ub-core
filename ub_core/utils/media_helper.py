import re
from enum import Enum, auto
from mimetypes import guess_extension
from os.path import basename, splitext
from urllib.parse import unquote_plus, urlparse

from multidict import CIMultiDictProxy
from pyrogram.enums import MessageMediaType
from pyrogram.types import Message, Story


class MediaType(Enum):
    AUDIO = auto()
    DOCUMENT = auto()
    GIF = auto()
    GROUP = auto()
    MESSAGE = auto()
    PHOTO = auto()
    STICKER = auto()
    VIDEO = auto()


class MediaExtensions:
    PHOTO = {".png", ".jpg", ".jpeg", ".heic", ".webp"}
    VIDEO = {".mp4", ".mkv", ".webm"}
    GIF = {".gif"}
    AUDIO = {".aac", ".mp3", ".opus", ".m4a", ".ogg", ".flac"}
    CODE = {".py", ".js", ".sh", ".bash", ".txt"}


ENUM_EXT_MAP = {
    MediaType.PHOTO: MediaExtensions.PHOTO,
    MediaType.VIDEO: MediaExtensions.VIDEO,
    MediaType.GIF: MediaExtensions.VIDEO,
    MediaType.AUDIO: MediaExtensions.AUDIO,
}


def bytes_to_mb(size: int):
    """Returns Size in MegaBytes"""
    return size // 1048576


def get_filename_from_url(url: str, tg_safe: bool = False) -> str:
    parsed_url = urlparse(unquote_plus(url))
    name = basename(parsed_url.path.rstrip("/"))
    return make_file_name_tg_safe(file_name=name) if tg_safe else name


def get_filename_from_headers(headers: dict | CIMultiDictProxy, tg_safe: bool = False) -> str | None:
    content_disposition = headers.get("Content-Disposition", "")

    match = re.search(r"filename=[\"']?(.*?)[\"']?(?:;|$)", string=content_disposition)

    if not match:
        return

    return make_file_name_tg_safe(match.group(1)) if tg_safe else match.group(1)


def get_filename_from_mime(mime_type: str, tg_safe: bool = False) -> None | str:
    extension = guess_extension(mime_type.strip())

    if not extension:
        return

    name = "file" + extension
    return make_file_name_tg_safe(name) if tg_safe else name


def make_file_name_tg_safe(file_name: str) -> str:
    """Rename TG File Type Ext to non TG File task_type Ext:
    .webp: a sticker
    .heic: not supported as Image
    .webm: Video Sticker
    """
    if file_name.lower().endswith((".webp", ".heic")):
        file_name += ".jpg"
    elif file_name.lower().endswith((".webm", ".mkv")):
        file_name += ".mp4"
    return file_name


def get_type(url: str | None = "", path: str | None = "", generic: bool = True) -> MediaType | None:
    if url:
        media = get_filename_from_url(url)
    else:
        media = path

    _, extension = splitext(media)

    for enum_type, extension_set in ENUM_EXT_MAP.items():
        if extension in extension_set:
            return enum_type

    if generic:
        return MediaType.DOCUMENT


MESSAGE_MEDIA_TYPES = {
    MessageMediaType.PHOTO,
    MessageMediaType.AUDIO,
    MessageMediaType.ANIMATION,
    MessageMediaType.VIDEO_NOTE,
    MessageMediaType.VIDEO,
    MessageMediaType.VOICE,
    MessageMediaType.STORY,
    MessageMediaType.DOCUMENT,
}


def get_tg_media_details(message: Message | Story):
    for media_type in MESSAGE_MEDIA_TYPES:
        if message.media == media_type:
            media = getattr(message, media_type.value, None)

            if media_type == MessageMediaType.PHOTO:
                media.file_name = "photo.png"
                return media

            if media_type == MessageMediaType.STORY:
                return get_tg_media_details(message.story)

            media.file_name = (
                getattr(media, "file_name", None)
                or get_filename_from_mime(getattr(media, "mime_type", None))
                or "file"
            )

            return media
    else:
        return None
