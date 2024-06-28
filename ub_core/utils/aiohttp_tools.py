import json
import logging
import os
from io import BytesIO

from aiohttp import ClientSession, ContentTypeError, web

from ub_core.config import Config
from ub_core.utils.media_helper import get_filename_from_url

LOGGER = logging.getLogger(Config.BOT_NAME)


class Aio:
    def __init__(self):
        """Setup aio object and params"""
        self.session: ClientSession | None = None
        self.app = None
        self.port = os.environ.get("API_PORT", 0)
        self.runner = None
        if self.port:
            Config.INIT_TASKS.append(self.set_site())
        Config.INIT_TASKS.append(self.set_session())

    async def close(self):
        """Gracefully Shutdown Clients"""
        if not self.session.closed:
            await self.session.close()
        if self.runner:
            await self.runner.cleanup()

    async def set_session(self):
        """Setup ClientSession on boot."""
        self.session = ClientSession()

    async def set_site(self):
        """Start A Dummy Website to pass Health Checks"""
        LOGGER.info("Starting Static WebSite.")
        self.app = web.Application()
        self.app.router.add_get(path="/", handler=self.handle_request)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(
            runner=self.runner,
            host="0.0.0.0",
            port=self.port,
            reuse_address=True,
            reuse_port=True,
        )
        await site.start()

    @staticmethod
    async def handle_request(_):
        return web.Response(text="Web Server Running...")

    async def get(
        self,
        url: str,
        json: bool = False,
        text: bool = False,
        content: bool = False,
        **kwargs,
    ):
        if json:
            return await self.get_json(url=url, **kwargs)

        if text:
            return await self.get_text(url=url, **kwargs)
        if content:
            return await self.get_content(url=url, **kwargs)

        raise TypeError(
            "aio.get method requires a type to fetch: json, text or content."
        )

    async def get_json(
        self,
        url: str,
        headers: dict = None,
        params: dict | str = None,
        json_: bool = False,
        timeout: int = 10,
    ) -> dict | None:
        try:
            async with self.session.get(
                url=url, headers=headers, params=params, timeout=timeout
            ) as ses:
                if json_:
                    return await ses.json()
                else:
                    return json.loads(await ses.text())  # fmt:skip
        except (json.JSONDecodeError, ContentTypeError):
            LOGGER.debug(await ses.text())
        except TimeoutError:
            LOGGER.debug(f"Timeout: {url}")

    async def get_text(
        self,
        url: str,
        headers: dict = None,
        params: dict | str = None,
        timeout: int = 10,
    ):
        try:
            async with self.session.get(
                url=url, headers=headers, params=params, timeout=timeout
            ) as ses:
                return await ses.text()
        except TimeoutError:
            LOGGER.debug(f"Timeout: {url}")

    async def get_content(
        self,
        url: str,
        headers: dict = None,
        params: dict | str = None,
        timeout: int = 10,
    ):
        try:
            async with self.session.get(
                url=url, headers=headers, params=params, timeout=timeout
            ) as ses:
                return await ses.content.read()
        except TimeoutError:
            LOGGER.debug(f"Timeout: {url}")

    async def in_memory_dl(self, url: str) -> BytesIO:
        async with self.session.get(url) as remote_file:
            bytes_data = await remote_file.read()
        file = BytesIO(bytes_data)
        file.name = get_filename_from_url(url, tg_safe=True)
        return file

    async def thumb_dl(self, thumb) -> BytesIO | str | None:
        if not thumb or not thumb.startswith("http"):
            return thumb
        return (await self.in_memory_dl(thumb))  # fmt:skip
