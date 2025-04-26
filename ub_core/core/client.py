import asyncio
import importlib
import logging
import sys
import traceback
from functools import cached_property
from inspect import iscoroutine, iscoroutinefunction
from os import getenv, path
from pathlib import Path
from signal import SIGINT, raise_signal
from typing import Self

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from ub_core import ub_core_dirname

from . import CustomDB
from .conversation import Conversation
from .decorators import CustomDecorators
from .methods import Methods
from .storage import FileStorage
from ..config import Config

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dir_name):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = Path(dir_name)

    modules = plugins_dir.rglob("**/[!^_]*.py")

    if dir_name == ub_core_dirname:
        modules = [str(m).split("site-packages/")[1] for m in modules]

    for py_module in modules:
        name = path.splitext(py_module)[0]
        py_name = name.replace("/", ".")
        try:
            mod = importlib.import_module(py_name)
            if hasattr(mod, "init_task"):
                Config.INIT_TASKS.append(mod.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class Bot(CustomDecorators, Methods, Client):
    def __init__(self, bot_token: str | None = None, session_string: str | None = None):
        name = Config.BOT_NAME + ("-bot" if bot_token else "")
        super().__init__(
            name=name,
            api_id=int(getenv("API_ID")),
            api_hash=getenv("API_HASH"),
            bot_token=bot_token,
            parse_mode=ParseMode.DEFAULT,
            sleep_threshold=30,
            storage_engine=FileStorage(name=name, session_string=session_string),
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

        session_string = getenv("SESSION_STRING")
        bot_token = getenv("BOT_TOKEN")

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

        db = CustomDB["COMMON_SETTINGS"]
        mode_data = await db.find_one({"_id": "client_mode"})
        if isinstance(mode_data, dict):
            Config.MODE = mode_data.get("value")

    @staticmethod
    def _import() -> None:
        """Import Inbuilt and external Modules"""
        import_modules(ub_core_dirname)
        import_modules(Config.WORKING_DIR)

        LOGGER.info("Plugins Imported.")

    @staticmethod
    async def _run_init_tasks():
        results = await asyncio.gather(*Config.INIT_TASKS, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                LOGGER.exception(result)

        Config.INIT_TASKS.clear()
        LOGGER.info("Init Tasks Completed.")

    async def boot(self) -> None:
        await super().start()

        LOGGER.info(f"[{self.client_type}] Connected to TG.")

        if self._bot:
            await self._bot.start()
            LOGGER.info(f"[BOT] Connected  to TG.")

        await asyncio.to_thread(self._import)

        await self.set_mode(force_bot=self.is_bot)

        await self._run_init_tasks()

        await self.log_text(text="<i>Started</i>")

        LOGGER.info(f"Idling on [{Config.MODE.upper()}] Mode...")

        self.is_idling = True
        await idle()

        await self.shut_down()

        sys.exit(self.exit_code)

    def raise_sigint(self):
        if self.user:
            self.user.exit_code = 69
        else:
            self.exit_code = 69
        raise_signal(SIGINT)

    async def restart_clients(self) -> bool:
        try:
            if self.user:
                await self.user.restart(block=False)
                await asyncio.sleep(1.5)
            if self.bot:
                await self.bot.restart(block=False)
                await asyncio.sleep(1.5)
            return True
        except Exception as e:
            traceback.print_exception(e)
            return False

    async def stop_clients(self) -> None:
        if self.user:
            await self.user.stop(block=False)
            await asyncio.sleep(1.5)

        if self.bot:
            await self.bot.stop(block=False)
            await asyncio.sleep(1.5)

    async def shut_down(self) -> None:
        """Gracefully ShutDown all Processes"""

        LOGGER.info("Stopping all processes and running Exit Tasks.")

        for task in Config.BACKGROUND_TASKS:
            if not task.done():
                task.cancel()

        for resource in Config.EXIT_TASKS:
            if resource is None:
                continue
            elif iscoroutinefunction(resource):
                await resource()
            elif iscoroutine(resource):
                await resource
            else:
                resource()

        await self.stop_clients()

        LOGGER.info("Exit Tasks Completed... Exiting...")
