import asyncio
import glob
import importlib
import logging
import os
import sys
from functools import cached_property
from inspect import iscoroutinefunction
from signal import SIGINT, raise_signal
from typing import Self

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from ub_core import ub_core_dirname

from .conversation import Conversation
from .db import DB_CLIENT, CustomDB
from .decorators import CustomDecorators
from .methods import Methods
from ..config import Config
from ..utils import aio

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dir_name):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = os.path.join(dir_name, "**/[!^_]*.py")
    modules = glob.glob(pathname=plugins_dir, recursive=True)

    if dir_name == ub_core_dirname:
        modules = [m.split("site-packages/")[1] for m in modules]

    for py_module in modules:
        name = os.path.splitext(py_module)[0]
        py_name = name.replace("/", ".")
        try:
            mod = importlib.import_module(py_name)
            if hasattr(mod, "init_task"):
                Config.INIT_TASKS.append(mod.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class Bot(CustomDecorators, Methods, Client):
    def __init__(self, bot_token: str | None = None, session_string: str | None = None):
        super().__init__(
            name=Config.BOT_NAME,
            api_id=int(os.environ.get("API_ID")),
            api_hash=os.environ.get("API_HASH"),
            bot_token=bot_token,
            session_string=session_string,
            parse_mode=ParseMode.DEFAULT,
            sleep_threshold=30,
            max_concurrent_transmissions=2,
        )
        self.log = LOGGER
        self.Convo = Conversation
        self.exit_code = 0

    @cached_property
    def is_bot(self):
        return self.me.is_bot

    @cached_property
    def is_user(self):
        return not self.me.is_bot


class DualClient(Bot):
    """A custom Class to Handle Both User and Bot client"""

    def __init__(self, force_bot: bool = False, _user: Self | None = None):
        """
        Initialise the class as per config vars.
        If both the bot token and string are available, boot into dual mode.
        if only a single var is available, boot into that specific mode.
        """
        self._bot = None
        self._user = _user
        self.is_idling = False

        session_string = os.environ.get("SESSION_STRING")
        bot_token = os.environ.get("BOT_TOKEN")

        if force_bot:
            # BOT INIT WHEN DUAL MODE
            super().__init__(bot_token=bot_token)
            return

        # DUAL
        if session_string:
            # USER
            super().__init__(session_string=session_string)
            # BOT
            if bot_token:
                self._bot = DualClient(force_bot=True, _user=self)
            return

        # BOT ONLY MODE
        super().__init__(bot_token=bot_token)

    @cached_property
    def bot(self) -> "DualClient":
        return self if self.is_bot else self._bot

    @cached_property
    def user(self) -> "DualClient":
        return self if self.is_user else self._user

    @property
    def client(self) -> "DualClient":
        return self.user if Config.MODE == "dual" else self.bot

    @property
    def client_type(self) -> str:
        return "User" if self.is_user else "Bot"

    @cached_property
    def has_bot(self) -> bool:
        return self._bot is not None

    @cached_property
    def has_user(self) -> bool:
        return self._user is not None

    @staticmethod
    async def set_mode(force_bot: bool = False):
        # If Booted Into Bot Client
        if force_bot:
            Config.MODE = "bot"
            return

        db = CustomDB("COMMON_SETTINGS")
        mode_data = await db.find_one({"_id": "client_mode"})
        if isinstance(mode_data, dict):
            Config.MODE = mode_data.get("value")

    @staticmethod
    def _import() -> None:
        """Import Inbuilt and external Modules"""
        import_modules(ub_core_dirname)
        import_modules(Config.WORKING_DIR)

    async def boot(self) -> None:
        await super().start()
        LOGGER.info(f"[{self.client_type}] Connected to TG.")
        if self._bot:
            await self._bot.start()
            LOGGER.info(f"[BOT] Connected  to TG.")

        await asyncio.to_thread(self._import)
        LOGGER.info("Plugins Imported.")

        await self.set_mode(force_bot=self.is_bot)

        await asyncio.gather(*Config.INIT_TASKS)
        Config.INIT_TASKS.clear()
        LOGGER.info("Init Tasks Completed.")

        await self.log_text(text="<i>Started</i>")
        LOGGER.info(f"Idling on [{Config.MODE.upper()}] Mode...")
        self.is_idling = True
        await idle()

        await self.shut_down()
        sys.exit(self.exit_code)

    def raise_sigint(self):
        self.exit_code = 69
        raise_signal(SIGINT)

    async def stop_clients(self) -> None:
        if self.user:
            await self.user.stop(block=True)
        if self.bot:
            await self.bot.stop(block=True)

    async def shut_down(self) -> None:
        """Gracefully ShutDown all Processes"""
        await self.stop_clients()

        for task in Config.BACKGROUND_TASKS:
            if not task.done():
                task.cancel()

        for resource in (DB_CLIENT, Config.REPO, aio):
            if resource is None:
                continue
            if iscoroutinefunction(resource.close):
                await resource.close()
            else:
                resource.close()

        LOGGER.info("Database, Git-Repository, and Aiohttp-Client connections closed.")
