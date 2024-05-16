import asyncio
import glob
import importlib
import logging
import os
import sys
from functools import cached_property

import psutil
from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from ub_core import DB_CLIENT, Config, ub_core_dirname
from ub_core.core.conversation import Conversation
from ub_core.core.decorators import CustomDecorators
from ub_core.core.methods import Methods
from ub_core.utils import aio

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dirname):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = os.path.join(dirname, "**/[!^_]*.py")
    modules = glob.glob(pathname=plugins_dir, recursive=True)

    if dirname == ub_core_dirname:
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


class BOT(CustomDecorators, Methods, Client):
    def __init__(self):
        super().__init__(
            name=Config.BOT_NAME,
            api_id=int(os.environ.get("API_ID")),
            api_hash=os.environ.get("API_HASH"),
            bot_token=os.environ.get("BOT_TOKEN"),
            session_string=os.environ.get("SESSION_STRING"),
            parse_mode=ParseMode.DEFAULT,
            sleep_threshold=30,
            max_concurrent_transmissions=2,
        )
        self.is_idling = False
        self.log = LOGGER
        self.Convo = Conversation

    @cached_property
    def is_bot(self):
        return self.me.is_bot

    @cached_property
    def is_user(self):
        return not self.me.is_bot

    async def boot(self) -> None:
        await super().start()
        LOGGER.info("Connected to TG.")
        await asyncio.to_thread(self._import)
        LOGGER.info("Plugins Imported.")
        await asyncio.gather(*Config.INIT_TASKS)
        Config.INIT_TASKS.clear()
        LOGGER.info("Init Tasks Completed.")
        await self.log_text(text="<i>Started</i>")
        LOGGER.info("Idling...")
        self.is_idling = True
        await idle()
        await self.shut_down()

    @staticmethod
    def _import():
        """Import Inbuilt and external Modules"""
        import_modules(ub_core_dirname)
        import_modules(Config.WORKING_DIR)

    @staticmethod
    async def shut_down():
        """Gracefully ShutDown all Processes"""
        await aio.close()

        for task in Config.BACKGROUND_TASKS:
            if not task.done():
                task.cancel()

        if DB_CLIENT is not None:
            LOGGER.info("DB Closed.")
            DB_CLIENT.close()
        if Config.REPO:
            Config.REPO.close()

        pid = os.getpid()
        open_files = psutil.Process(pid).open_files()
        net_connections = [conn for conn in psutil.net_connections() if conn.pid == pid]

        for handler in open_files + net_connections:
            try:
                os.close(handler.fd)
            except Exception as e:
                LOGGER.error(e, exc_info=True)

    async def restart(self, hard=False) -> None:
        await self.shut_down()
        await super().stop(block=False)

        if hard:
            os.execl("/bin/bash", "/bin/bash", "run")

        LOGGER.info("Restarting...")
        os.execl(sys.executable, sys.executable, "-m", Config.WORKING_DIR)
