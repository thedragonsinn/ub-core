import asyncio
import importlib
import logging
import os
import pathlib
import signal
import sys
import typing

import pyrogram

from ub_core import ub_core_dirname

from . import CustomDB
from .conversation import Conversation
from .decorators import CustomDecorators
from .methods import Methods
from ..config import Config

LOGGER = logging.getLogger(Config.BOT_NAME)
EXIT_CODE = 0


def import_modules(dir_name):
    """Import Plugins and add init_task to Task Manager"""
    top_path = pathlib.Path(dir_name).expanduser().resolve()
    root = top_path.name

    for module in top_path.rglob("[!^_]*.py"):
        parts = module.with_suffix("").parts
        name_index = parts.index(root)
        # converted to relative paths
        # site-packages for core
        py_name = ".".join(parts[name_index:])

        try:
            mod = importlib.import_module(py_name)
            if hasattr(mod, "init_task"):
                Config.TASK_MANAGER.add_init(mod.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class Bot(CustomDecorators, Methods, pyrogram.Client):
    def __init__(self, bot_token: str | None = None, session_string: str | None = None):
        name = Config.BOT_NAME + ("-bot" if bot_token else "")
        super().__init__(
            name=name,
            api_id=int(os.getenv("API_ID")),
            api_hash=os.getenv("API_HASH"),
            bot_token=bot_token,
            in_memory=False,
            parse_mode=pyrogram.enums.ParseMode.DEFAULT,
            session_string=session_string,
            sleep_threshold=60,
            max_concurrent_transmissions=4,
            max_message_cache_size=1000,
            max_business_user_connection_cache_size=1000,
        )
        self.log = LOGGER
        self.Convo = Conversation

    @property
    def is_bot(self):
        return self.me.is_bot

    @property
    def is_user(self):
        return not self.me.is_bot


class DualClient(Bot):
    """A custom Class to Handle Both User and Bot client"""

    def __init__(self, force_bot: bool = False, _user: typing.Self | None = None):
        """
        Initialise the class as per config vars.
        If both the bot token and string are available, boot into dual mode.
        if only a single var is available, boot into that specific mode.
        """
        self._bot = None
        self._user = _user
        self.is_idling = False

        session_string = os.getenv("SESSION_STRING")
        bot_token = os.getenv("BOT_TOKEN")

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

    @property
    def bot(self) -> "DualClient":
        return self if self.is_bot else self._bot

    @property
    def user(self) -> "DualClient":
        return self if self.is_user else self._user

    @property
    def client(self) -> "DualClient":
        return self.user if Config.MODE == "dual" else self.bot

    @property
    def client_type(self) -> str:
        return "User" if self.is_user else "Bot"

    @property
    def has_bot(self) -> bool:
        return self._bot is not None

    @property
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

    async def boot(self) -> None:
        Config.TASK_MANAGER.loop = self.loop

        await super().start()

        LOGGER.info(f"[{self.client_type}] Connected to TG.")

        if self._bot:
            await self._bot.start()
            LOGGER.info("[BOT] Connected  to TG.")

        await asyncio.to_thread(self._import)
        await self.set_mode(force_bot=self.is_bot)
        await Config.TASK_MANAGER.run_init_tasks()

        await self.log_text(text="<i>Started</i>")
        LOGGER.info(f"Idling on [{Config.MODE.upper()}] Mode...")
        self.is_idling = True
        await pyrogram.idle()

        await self.shut_down()

        # for readability of logs.
        LOGGER.info(f"\n\n{'#' * 10} < End of run > {'#' * 10}\n\n", extra={"raw": True})
        global EXIT_CODE
        sys.exit(EXIT_CODE)

    def raise_sigint(self):
        global EXIT_CODE
        EXIT_CODE = 69
        signal.raise_signal(signal.SIGINT)

    async def stop_clients(self) -> None:
        if self.user:
            await self.user.stop(block=False)
            await asyncio.sleep(1.5)

        if self.bot:
            await self.bot.stop(block=False)
            await asyncio.sleep(1.5)

    async def shut_down(self) -> None:
        """Gracefully ShutDown all Processes"""
        global EXIT_CODE
        LOGGER.info("Stopping all processes...")
        await Config.TASK_MANAGER.close_and_run_exit_tasks()
        await self.stop_clients()
        LOGGER.info(f"Exiting with code: {EXIT_CODE}")
