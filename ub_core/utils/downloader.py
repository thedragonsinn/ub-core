import asyncio
import os
import shutil
from functools import cached_property
from typing import TYPE_CHECKING

import aiofiles
import aiohttp

from .helpers import progress
from .media_helper import (
    bytes_to_mb,
    get_filename_from_headers,
    get_filename_from_url,
    get_type,
)

if TYPE_CHECKING:
    from ub_core import Message


class DownloadedFile:
    def __init__(self, name: str, dir: str, size: int | float):
        self.dir = dir
        self.name = name
        self.path = os.path.join(dir, name)
        self.size = size
        self.type = get_type(path=name)

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
        dl_obj = await Download.setup(
            url="https....",
            path="downloads",
            message_to_edit=response,
        )
        file = await dl_obj.download()
    """

    def __init__(
        self,
        url: str,
        dir: str,
        file_session: aiohttp.ClientResponse,
        session: aiohttp.client,
        headers: aiohttp.ClientResponse.headers,
        custom_file_name: str | None = None,
        message_to_edit: "Message" = None,
    ):
        self.custom_file_name: str = custom_file_name
        self.dir: str = dir
        os.makedirs(name=dir, exist_ok=True)

        self.file_session: aiohttp.ClientResponse = file_session
        self.session: aiohttp.ClientSession = session
        self.url: str = url
        self.headers: aiohttp.ClientResponse.headers = headers

        self.raw_completed_size: int = 0

        self.has_started: bool = False
        self.is_done: bool = False

        self.message_to_edit: "Message" = message_to_edit
        self.progress_task: asyncio.Task | None = None

    @classmethod
    async def setup(
        cls,
        url: str,
        dir: str = "downloads",
        message_to_edit: "Message" = None,
        custom_file_name: str | None = None,
    ) -> "Download":
        session = aiohttp.ClientSession()
        file_session = await session.get(url=url)
        headers = file_session.headers
        cls_object = cls(
            url=url,
            dir=dir,
            file_session=file_session,
            session=session,
            headers=headers,
            message_to_edit=message_to_edit,
            custom_file_name=custom_file_name,
        )
        await asyncio.gather(
            cls_object.check_disk_space(), cls_object.check_duplicates()
        )
        return cls_object

    async def check_disk_space(self) -> None:
        if shutil.disk_usage(self.dir).free < self.raw_size:
            await self.close()
            raise OverflowError(
                f"Not enough space in {self.dir} to download {self.size} mb."
            )

    async def check_duplicates(self) -> None:
        if os.path.isfile(self.file_path):
            await self.close()
            raise FileExistsError(f"{self.file_path} already exists!!!")

    @property
    def completed_size(self) -> int:
        """Size in MB"""
        return bytes_to_mb(self.raw_completed_size)

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
    def raw_size(self) -> int:
        # File Size in Bytes
        return int(self.headers.get("Content-Length", 0))

    @cached_property
    def size(self) -> int:
        """File size in MBs"""
        return bytes_to_mb(self.raw_size)

    async def close(self) -> None:
        if not self.session.closed:
            await self.session.close()

        if not self.file_session.closed:
            self.file_session.close()

        if not self.progress_task.done():
            self.progress_task.cancel()

    async def download(self) -> DownloadedFile | Exception | None:
        if self.session.closed or self.file_session.closed:
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
            async for file_chunk in self.file_session.content.iter_chunked(5120):
                await async_file.write(file_chunk)  # NOQA
                self.raw_completed_size += 5120

    async def edit_progress(self) -> None:
        while not self.is_done:
            await progress(
                current_size=self.raw_completed_size,
                total_size=self.raw_size or 1,
                response=self.message_to_edit,
                action_str="Downloading...",
                file_path=self.file_path,
            )
            await asyncio.sleep(8)

    def return_file(self) -> DownloadedFile:
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(self.file_path)

        return DownloadedFile(name=self.file_name, dir=self.dir, size=self.size)
