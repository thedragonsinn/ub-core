import re
from enum import Enum, auto
from mimetypes import guess_extension
from os.path import basename, splitext
from urllib.parse import unquote_plus, urlparse

from multidict import CIMultiDictProxy
from pyrogram.enums import MessageMediaType
from pyrogram.types import Message


class MediaType(Enum):
    AUDIO = auto()
    DOCUMENT = auto()
    GIF = auto()
    GROUP = auto()
    MESSAGE = auto()
    PHOTO = auto()
    STICKER = auto()
    VIDEO = auto()


class MediaExts:
    PHOTO = {".png", ".jpg", ".jpeg", ".heic", ".webp"}
    VIDEO = {".mp4", ".mkv", ".webm"}
    GIF = {".gif"}
    AUDIO = {".aac", ".mp3", ".opus", ".m4a", ".ogg", ".flac"}


def bytes_to_mb(size: int):
    """Returns Size in MegaBytes"""
    return size // 1048576


def get_filename_from_url(url: str, tg_safe: bool = False) -> str:
    parsed_url = urlparse(unquote_plus(url))
    name = basename(parsed_url.path.rstrip("/"))
    return make_file_name_tg_safe(file_name=name) if tg_safe else name


def get_filename_from_headers(
    headers: dict | CIMultiDictProxy, tg_safe: bool = False
) -> str | None:
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
    """Rename TG File Type Ext to non TG File type Ext:
    .webp: a sticker
    .heic: not supported as Image
    .webm: Video Sticker
    """
    if file_name.lower().endswith((".webp", ".heic")):
        file_name = file_name + ".jpg"
    elif file_name.lower().endswith((".webm", ".mkv")):
        file_name = file_name + ".mp4"
    return file_name


def get_type(url: str | None = "", path: str | None = "", generic: bool = True) -> MediaType | None:
    if url:
        media = get_filename_from_url(url)
    else:
        media = path

    name, ext = splitext(media)

    if ext in MediaExts.PHOTO:
        return MediaType.PHOTO

    if ext in MediaExts.VIDEO:
        return MediaType.VIDEO

    if ext in MediaExts.GIF:
        return MediaType.GIF

    if ext in MediaExts.AUDIO:
        return MediaType.AUDIO

    if generic:
        return MediaType.DOCUMENT


def get_tg_media_details(message: Message):
    match message.media:
        case MessageMediaType.PHOTO:
            media = message.photo
            media.file_name = "photo.png"
        case MessageMediaType.AUDIO:
            media = message.audio
        case MessageMediaType.ANIMATION:
            media = message.animation
        case MessageMediaType.DOCUMENT:
            media = message.document
        case MessageMediaType.STICKER:
            media = message.sticker
        case MessageMediaType.VIDEO:
            media = message.video
        case MessageMediaType.VOICE:
            media = message.voice
        case MessageMediaType.STORY:
            media = get_tg_media_details(message.story)
        case _:
            return

    media.file_name = (
        getattr(media, "file_name", None)
        or get_filename_from_mime(getattr(media, "mime_type", None))
        or "file"
    )

    return media
