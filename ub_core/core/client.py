import asyncio
import glob
import importlib
import logging
import os
import sys
from functools import cached_property

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from ub_core import DB_CLIENT, Config, ub_core_dirname
from ub_core.core.conversation import Conversation
from ub_core.core.decorators.add_cmd import AddCmd
from ub_core.core.methods import ChannelLogger, SendMessage
from ub_core.utils import aio

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dirname):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = os.path.join(dirname, "**/[!^_]*.py")
    for py_module in glob.glob(pathname=plugins_dir, recursive=True):
        module_path, module_name = py_module, os.path.basename(py_module)
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "init_task"):
                Config.INIT_TASKS.append(module.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class BOT(AddCmd, SendMessage, ChannelLogger, Client):
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
        self._import()
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

    async def restart(self, hard=False) -> None:
        await self.shut_down()
        await super().stop(block=False)
        if hard:
            os.execl("/bin/bash", "/bin/bash", "run")
        LOGGER.info("Restarting...")
        os.execl(sys.executable, sys.executable, "-m", Config.WORKING_DIR)
