import asyncio
import glob
import importlib
import logging
import os
import sys
from functools import cached_property

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from ub_core import DB_CLIENT, Config, CustomDB, ub_core_dirname
from ub_core.core.conversation import Conversation
from ub_core.core.decorators.add_cmd import AddCmd
from ub_core.core.methods import ChannelLogger, SendMessage
from ub_core.utils import aio

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dirname):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = os.path.join(dirname, "**/[!^_]*.py")
    modules = glob.glob(pathname=plugins_dir, recursive=True)
    if dirname == ub_core_dirname:
        modules = [m.split("site-packages/")[1] for m in modules]
    for py_module in modules:
        try:
            name = os.path.splitext(py_module)[0]
            py_name = name.replace("/", ".")
            mod = importlib.import_module(py_name)
            if hasattr(mod, "init_task"):
                Config.INIT_TASKS.append(mod.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class Bot(AddCmd, SendMessage, ChannelLogger, Client):
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

    @cached_property
    def is_bot(self):
        return self.me.is_bot

    @cached_property
    def is_user(self):
        return not self.me.is_bot


class DualClient(Bot):
    """A custom Class to Handle Both User and Bot client"""

    def __init__(self, force_bot: bool = False, _user: Bot | None = None):
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
    def bot(self):
        return self if self.is_bot else self._bot

    @cached_property
    def user(self):
        return self if self.is_user else self._user

    @property
    def client(self):
        return self if Config.MODE == "dual" else self.bot

    @cached_property
    def has_bot(self):
        return self._bot is not None

    @cached_property
    def has_user(self):
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
    def _import():
        """Import Inbuilt and external Modules"""
        import_modules(ub_core_dirname)
        import_modules(Config.WORKING_DIR)

    async def boot(self) -> None:
        await super().start()
        if self._bot:
            await self._bot.start()
        LOGGER.info("Connected to TG.")

        self._import()
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

    async def restart(self, hard=False) -> None:
        await self.shut_down()
        if hard:
            os.execl("/bin/bash", "/bin/bash", "run")
        LOGGER.info("Restarting...")
        os.execl(sys.executable, sys.executable, "-m", Config.WORKING_DIR)

    async def stop_clients(self):
        await super().stop(block=False)
        if self._bot:
            await self._bot.stop(block=False)

    async def shut_down(self):
        """Gracefully ShutDown all Processes"""

        await self.stop_clients()

        await aio.close()

        for task in Config.BACKGROUND_TASKS:
            if not task.done():
                task.cancel()

        if DB_CLIENT is not None:
            LOGGER.info("DB Closed.")
            DB_CLIENT.close()
        if Config.REPO:
            Config.REPO.close()
