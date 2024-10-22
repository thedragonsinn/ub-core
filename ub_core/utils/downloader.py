import asyncio
import os
import shutil
from functools import cached_property

import aiofiles
from aiohttp import ClientResponse, ClientSession
from pyrogram.types import Message

from .helpers import progress
from .media_helper import (
    bytes_to_mb,
    get_filename_from_headers,
    get_filename_from_url,
    get_type,
)


class DownloadedFile:
    def __init__(self, file: str, size: int = 0):
        # Folder
        self.dir = os.path.dirname(file)
        # Name
        self.name = os.path.basename(file)
        # Folder + Name
        self.path = os.path.join(self.dir, self.name)
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
        dir (str):
            download path without file name.
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
        dir: str,
        custom_file_name: str | None = None,
        message_to_edit: "Message" = None,
    ):
        self.url: str = url
        self.custom_file_name: str = custom_file_name
        self.message_to_edit: "Message" = message_to_edit

        self.dir: str = dir
        os.makedirs(name=dir, exist_ok=True)

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
        self.file_response_session = await self.client_session.get(url=self.url)
        self.headers = self.file_response_session.headers

    async def __aenter__(self) -> "Download":
        await self.set_sessions()
        self.check_duplicates()
        self.check_disk_space()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

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

    def check_disk_space(self) -> None:
        if shutil.disk_usage(self.dir).free < self.size_bytes:
            raise OSError(f"Not enough space in {self.dir} to download {self.size} mb.")

    def check_duplicates(self) -> None:
        if os.path.isfile(self.file_path):
            raise FileExistsError(f"{self.file_path} already exists!!!")

    @property
    def completed_size(self) -> int:
        """Size in MB"""
        return bytes_to_mb(self.completed_size_bytes)

    @cached_property
    def file_name(self) -> str:
        if self.custom_file_name:
            return self.custom_file_name
        return get_filename_from_headers(self.headers) or get_filename_from_url(
            self.url
        )

    @cached_property
    def file_path(self) -> str:
        return os.path.join(self.dir, self.file_name)

    @cached_property
    def size_bytes(self) -> int:
        # File Size in Bytes
        return int(self.headers.get("Content-Length", 0))

    @cached_property
    def size(self) -> int:
        """File size in MBs"""
        return bytes_to_mb(self.size_bytes)

    async def close(self) -> None:
        if not self.client_session.closed:
            await self.client_session.close()

        if not self.file_response_session.closed:
            self.file_response_session.close()

        if not self.progress_task.done():
            self.progress_task.cancel()

    async def download(self) -> DownloadedFile | Exception | None:
        if self.client_session.closed or self.file_response_session.closed:
            return

        self.has_started = True
        self.progress_task = asyncio.create_task(self.edit_progress())

        exc = None
        try:
            await self.write_file()
        except Exception as e:
            exc = e
        finally:
            self.is_done = True
            await self.close()

        return exc or self.return_file()

    async def write_file(self) -> None:
        async with aiofiles.open(self.file_path, "wb") as async_file:
            async for file_chunk in self.file_response_session.content.iter_chunked(
                5120
            ):
                await async_file.write(file_chunk)  # NOQA
                self.completed_size_bytes += 5120

    async def edit_progress(self) -> None:
        if not isinstance(self.message_to_edit, Message):
            return

        while not self.is_done:
            await progress(
                current_size=self.completed_size_bytes,
                total_size=self.size_bytes or 1,
                response=self.message_to_edit,
                action_str="Downloading...",
                file_path=self.file_path,
            )
            await asyncio.sleep(8)

    def return_file(self) -> DownloadedFile:
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(self.file_path)

        return DownloadedFile(os.path.join(self.dir, self.file_name))
