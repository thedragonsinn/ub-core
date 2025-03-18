import asyncio
import json
import logging
import os
from collections.abc import Callable
from functools import wraps
from io import BytesIO

from aiohttp import ClientSession, ContentTypeError, web
from yarl import URL

from .media_helper import (
    get_filename_from_headers,
    get_filename_from_mime,
    get_filename_from_url,
    get_type,
)
from ..config import Config

LOGGER = logging.getLogger(Config.BOT_NAME)


class AioServer:
    def __init__(self):
        self.app: web.Application | None = None
        self.runner: web.AppRunner | None = None
        self.routes: list[web.RouteDef] = []

        self.site: web.TCPSite | None = None
        self.port = os.environ.get("API_PORT", 0)

        if self.port:
            Config.INIT_TASKS.append(self.start())
            Config.EXIT_TASKS.append(self.close)
            self.set_health_check_handler()

    async def start(self):
        await self.set_app()
        await self.set_routes()
        await self.set_runner()
        await self.set_site()

    async def close(self):
        if self.runner:
            await self.runner.cleanup()

    async def set_app(self):
        LOGGER.debug("Setting up WebApp.")
        self.app = web.Application()

    async def set_routes(self):
        LOGGER.debug("Setting up Routes.")
        self.app.add_routes(self.routes)
        LOGGER.debug(f"Added {len(self.routes)} routes.")

    async def set_runner(self):
        LOGGER.debug("Starting Runner.")
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

    async def set_site(self):
        """Start A Dummy Website to pass Health Checks"""
        LOGGER.info("Starting Static WebSite.")
        self.site = web.TCPSite(
            runner=self.runner, host="0.0.0.0", port=self.port, reuse_address=True, reuse_port=True
        )
        await self.site.start()

    def is_running(self) -> bool:
        # noinspection PyProtectedMember
        return self.site._server.is_serving() if self.site else False

    @staticmethod
    def ensure_not_running(func):
        @wraps(func)
        def inner(self, *args, **kwargs):
            if self.is_running():
                raise RuntimeError("Can't perform operations on already running server.")

            return func(self, *args, **kwargs)

        return inner

    @ensure_not_running
    def add_route(
        self,
        method: str,
        path: str,
        handler: Callable,
        name: str = None,
        allow_head: bool = True,
        **kwargs,
    ) -> web.RouteDef:
        route = web.route(
            method=method.upper(),
            path=path,
            handler=handler,
            name=name,
            allow_head=allow_head,
            **kwargs,
        )
        LOGGER.debug(repr(route))
        self.routes.append(route)
        return route

    @ensure_not_running
    def set_health_check_handler(self) -> web.RouteDef:
        return self.add_route(
            method="GET", path="/", handler=self.handle_health_check_request, name="HEALTH_CHECK"
        )

    @staticmethod
    async def handle_health_check_request(request):
        LOGGER.debug(repr(request))
        return web.Response(text="Web Server Running...")


class Aio:

    def __init__(self):
        """Setup aio object and params"""
        self.session: ClientSession | None = None

        Config.INIT_TASKS.append(self.set_session())
        Config.EXIT_TASKS.append(self.close)

        self.server: AioServer = AioServer()

        self.ping_interval = int(os.environ.get("PING_INTERVAL", 240))
        self.ping_url = os.environ.get("PING_URL")

        if self.ping_url:
            LOGGER.info(
                f"Starting Auto-Ping Task at {self.ping_url} with {self.ping_interval} seconds interval."
            )
            Config.BACKGROUND_TASKS.append(asyncio.create_task(self.ping_website()))

    async def set_session(self):
        """Setup ClientSession on boot."""
        LOGGER.info("AioHttp Session Created.")
        self.session = ClientSession()

    async def close(self):
        """Gracefully Shutdown Clients"""
        if not self.session.closed:
            await self.session.close()

    async def ping_website(self):
        await asyncio.sleep(30)
        await self.get_text(url=self.ping_url)

        total_seconds = 0
        while 1:
            total_seconds += self.ping_interval
            await asyncio.sleep(self.ping_interval)
            if not await self.get_text(url=self.ping_url):
                LOGGER.info(
                    f"Unsuccessful ping task wake-up at {total_seconds//3600} hours after boot."
                )

    async def get(
        self, url: str, json: bool = False, text: bool = False, content: bool = False, **kwargs
    ):
        if json:
            return await self.get_json(url=url, **kwargs)

        if text:
            return await self.get_text(url=url, **kwargs)
        if content:
            return await self.get_content(url=url, **kwargs)

        raise TypeError("aio.get method requires a type to fetch: json, text or content.")

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
        self, url: str, headers: dict = None, params: dict | str = None, timeout: int = 10
    ):
        try:
            async with self.session.get(
                url=url, headers=headers, params=params, timeout=timeout
            ) as ses:
                return await ses.text()
        except TimeoutError:
            LOGGER.debug(f"Timeout: {url}")

    async def get_content(
        self, url: str, headers: dict = None, params: dict | str = None, timeout: int = 10
    ):
        try:
            async with self.session.get(
                url=url, headers=headers, params=params, timeout=timeout
            ) as ses:
                return await ses.content.read()
        except TimeoutError:
            LOGGER.debug(f"Timeout: {url}")

    async def in_memory_dl(self, url: str, encoded: bool = False) -> BytesIO:
        async with self.session.get(URL(url, encoded=encoded)) as remote_file:
            headers = remote_file.headers
            mime = headers.get("Content-Type", "")
            bytes_data = await remote_file.read()
            file = BytesIO(bytes_data)

        name_from_url = get_filename_from_url(url=url, tg_safe=True)
        name_from_mime = get_filename_from_mime(mime_type=mime, tg_safe=True)
        name_from_headers = get_filename_from_headers(headers=headers, tg_safe=True)

        media_type = get_type(path=name_from_url, generic=False)

        # Set name from Headers
        if name_from_headers:
            file.name = name_from_headers
        # URL has a valid media type filename
        elif media_type:
            file.name = name_from_url
        # Try to guess from mime-header
        elif name_from_mime:
            file.name = name_from_mime
        # Fallback to whatever name is extracted from url
        else:
            file.name = name_from_url

        return file

    async def thumb_dl(self, thumb, encoded: bool = False) -> BytesIO | str | None:
        if not thumb or not thumb.startswith("http"):
            return thumb
        return await self.in_memory_dl(url=thumb, encoded=encoded)
