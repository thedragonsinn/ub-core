import asyncio
import os
import shutil
from collections.abc import AsyncIterator
from functools import cached_property
from pathlib import Path

import aiofiles
from aiohttp import ClientResponse, ClientSession
from pyrogram.types import Message
from yarl import URL

from .helpers import progress
from .media_helper import (
    bytes_to_mb,
    get_filename_from_headers,
    get_filename_from_mime,
    get_filename_from_url,
    get_type,
)


class DownloadedFile:
    def __init__(self, file: str | Path, size: int = 0):
        file_path = Path(file)

        # Folder
        self.dir = file_path.parent
        # Name
        self.name = file_path.name
        # Folder + Name
        self.path = str(file_path)
        # Size in MB
        self.size = bytes_to_mb(size or os.path.getsize(self.path))
        # Media Type
        self.type = get_type(path=self.name)

    def __str__(self):
        return self.path


class Download:
    """Download a file in async using aiohttp.

    Parameters:
        url (str):
            file url.
        dir (str | Path):
            download path without file name.
        is_encoded_url (bool):
            pass True if the url is already encoded and is sensitive.
        message_to_edit(Message):
            response message to edit for progress.
        custom_file_name(str):
            override the file name.

    Returns:
        ON success a DownloadedFile object is returned.

    Methods:
        # New cleaner method
        async with Download(url, dir, response) as downloader:
            file = await downloader.download()

        OR

        # Legacy method, kept for backwards compatibility.
        dl_obj = await Download.setup(
            url="https....",
            dir="downloads",
            message_to_edit=response,
        )
        file = await dl_obj.download()
    """

    def __init__(
        self,
        url: str,
        dir: str | Path,
        is_encoded_url: bool = False,
        custom_file_name: str | None = None,
        message_to_edit: "Message" = None,
        use_tg_safe_name: bool = False,
    ):
        self.url: str = url
        self.is_encoded_url = is_encoded_url
        self.custom_file_name: str = custom_file_name
        self.use_tg_safe_name = use_tg_safe_name
        self.message_to_edit: "Message" = message_to_edit

        self.dir: Path = Path(dir)
        self.dir.mkdir(parents=True, exist_ok=True)

        # noinspection PyTypeChecker
        self.client_session: "ClientSession" = None
        # noinspection PyTypeChecker
        self.file_response_session: "ClientResponse" = None
        self.headers: "ClientResponse.headers" = None

        self.completed_size_bytes: int = 0
        self.is_done: bool = False
        self.progress_task: asyncio.Task | None = None

    async def set_sessions(self):
        self.client_session = ClientSession()
        self.file_response_session = await self.client_session.get(
            url=URL(self.url, encoded=self.is_encoded_url)
        )
        self.headers = self.file_response_session.headers

    async def __aenter__(self) -> "Download":
        await self.set_sessions()
        self.check_duplicates()
        self.check_disk_space()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        if not self.client_session.closed:
            await self.client_session.close()

        if not self.file_response_session.closed:
            self.file_response_session.close()

        if self.progress_task and not self.progress_task.done():
            self.progress_task.cancel()

    @classmethod
    async def setup(
        cls,
        url: str,
        dir: str = "downloads",
        message_to_edit: "Message" = None,
        custom_file_name: str | None = None,
    ) -> "Download":

        cls_object = cls(
            url=url,
            dir=dir,
            message_to_edit=message_to_edit,
            custom_file_name=custom_file_name,
        )
        await cls_object.set_sessions()
        return cls_object

    async def download(self) -> DownloadedFile | None:
        if self.client_session.closed or self.file_response_session.closed:
            return

        self.progress_task = asyncio.create_task(self.edit_progress())

        try:
            await self.write_file()
            return self.return_file()
        finally:
            self.is_done = True
            await self.close()

    async def iter_chunks(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        """
        @param chunk_size: size in bytes. defaults to 65536 (64kb)
        @return: AsyncGenerator
        """
        async for chunk in self.file_response_session.content.iter_chunked(chunk_size):
            yield chunk

    def check_disk_space(self) -> None:
        if shutil.disk_usage(self.dir).free < self.size_bytes:
            raise OSError(f"Not enough space in {self.dir} to download {self.size} mb.")

    def check_duplicates(self) -> None:
        if self.file_path.exists():
            raise FileExistsError(f"{self.file_path} already exists!!!")

    @property
    def completed_size(self) -> int:
        """Size in MB"""
        return bytes_to_mb(self.completed_size_bytes)

    @cached_property
    def file_name(self) -> str:
        if self.custom_file_name:
            return self.custom_file_name

        name_from_headers = get_filename_from_headers(self.headers, tg_safe=self.use_tg_safe_name)
        if name_from_headers:
            return name_from_headers

        name_from_url = get_filename_from_url(self.url, tg_safe=self.use_tg_safe_name)

        # if URL has a valid media type filename
        if get_type(path=name_from_url, generic=False):
            return name_from_url

        # Try to guess from mime-header
        name_from_mime = get_filename_from_mime(
            self.headers.get("Content-Type", ""), tg_safe=self.use_tg_safe_name
        )

        # if mime fails fallback to whatever name is extracted from url
        return name_from_mime or name_from_url

    @cached_property
    def file_path(self) -> Path:
        return self.dir / self.file_name

    @cached_property
    def size_bytes(self) -> int:
        # File Size in Bytes
        return int(self.headers.get("Content-Length", 0))

    @cached_property
    def size(self) -> int:
        """File size in MBs"""
        return bytes_to_mb(self.size_bytes)

    async def write_file(self) -> None:
        async with aiofiles.open(file=self.file_path, mode="wb") as async_file:
            async for chunk in self.iter_chunks():
                await async_file.write(chunk)
                self.completed_size_bytes += len(chunk)

    async def edit_progress(self) -> None:
        if not isinstance(self.message_to_edit, Message):
            return

        while not self.is_done:
            await progress(
                current_size=self.completed_size_bytes,
                total_size=self.size_bytes or 1,
                response=self.message_to_edit,
                action_str="Downloading...",
                file_path=str(self.file_path),
            )
            await asyncio.sleep(8)

    def return_file(self) -> DownloadedFile:
        if not self.file_path.is_file():
            raise FileNotFoundError(self.file_path)

        return DownloadedFile(self.file_path)
