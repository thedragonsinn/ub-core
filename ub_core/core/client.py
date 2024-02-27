import asyncio
import glob
import importlib
import logging
import os
import sys

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from ub_core import DB_CLIENT, Config, ub_core_dirname
from ub_core.core.conversation import Conversation
from ub_core.core.decorators.add_cmd import AddCmd
from ub_core.core.methods import ChannelLogger, SendMessage
from ub_core.utils.aiohttp_tools import aio

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(plugins_dir):
    for py_module in glob.glob(pathname=plugins_dir, recursive=True):
        name = os.path.splitext(py_module)[0]
        py_name = name.replace("/", ".")
        print(py_name)
        try:
            mod = importlib.import_module(py_name)
            if hasattr(mod, "init_task"):
                Config.INIT_TASKS.append(mod.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class BOT(AddCmd, SendMessage, ChannelLogger, Client):
    def __init__(self):
        super().__init__(
            name="bot",
            api_id=int(os.environ.get("API_ID")),
            api_hash=os.environ.get("API_HASH"),
            bot_token=os.environ.get("BOT_TOKEN"),
            session_string=os.environ.get("SESSION_STRING"),
            parse_mode=ParseMode.DEFAULT,
            sleep_threshold=30,
            max_concurrent_transmissions=2,
        )
        self.log = LOGGER
        self.Convo = Conversation

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
        await idle()
        await self.shut_down()

    @staticmethod
    def _import():
        [
            import_modules(path)
            for path in (
                Config.WORKING_DIR + "/**/[!^_]*.py",
                ub_core_dirname + "/**/[!^_]*.py",
            )
        ]

    @staticmethod
    async def shut_down():
        await aio.close()
        for task in Config.BACKGROUND_TASKS:
            if not task.done():
                task.cancel()
        if DB_CLIENT is not None:
            LOGGER.info("DB Closed.")
            DB_CLIENT.close()

    async def restart(self, hard=False) -> None:
        await self.shut_down()
        await super().stop(block=False)
        if hard:
            os.execl("/bin/bash", "/bin/bash", "run")
        LOGGER.info("Restarting...")
        os.execl(sys.executable, sys.executable, "-m", Config.WORKING_DIR)


bot: BOT = BOT()
