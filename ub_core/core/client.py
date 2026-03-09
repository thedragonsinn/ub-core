import asyncio
import importlib
import logging
import os
import signal
import sys
from functools import cached_property
from pathlib import Path

import pyrogram

from ub_core import ub_core_dirname

from .conversation import Conversation as Convo
from .decorators import CustomDecorators
from .methods import Methods
from ..config import Config

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dir_name):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = Path(dir_name)

    modules = plugins_dir.rglob("**/[!^_]*.py")

    if dir_name == ub_core_dirname:
        modules = [str(m).split("site-packages/")[1] for m in modules]

    for py_module in modules:
        name = os.path.splitext(py_module)[0]
        py_name = name.replace("/", ".")
        try:
            mod = importlib.import_module(py_name)
            if hasattr(mod, "init_task"):
                Config.TASK_MANAGER.add_init(mod.init_task())
        except Exception as ie:
            LOGGER.error(ie, exc_info=True)


class BOT(CustomDecorators, Methods, pyrogram.Client):
    def __init__(self):
        bot_token = os.getenv("BOT_TOKEN")
        name = Config.BOT_NAME + ("-bot" if bot_token else "")
        super().__init__(
            name=name,
            api_id=int(os.getenv("API_ID")),
            api_hash=os.getenv("API_HASH"),
            bot_token=bot_token,
            in_memory=False,
            session_string=os.getenv("SESSION_STRING"),
            sleep_threshold=30,
            max_concurrent_transmissions=2,
        )

        self.is_idling = False
        self.log = LOGGER
        self.Convo = Convo
        self.exit_code = 0

    @cached_property
    def is_bot(self) -> bool:
        return self.me.is_bot

    @cached_property
    def is_user(self) -> bool:
        return not self.me.is_bot

    @staticmethod
    def _import() -> None:
        """Import Inbuilt and external Modules"""
        import_modules(ub_core_dirname)
        import_modules(Config.WORKING_DIR)
        LOGGER.info("Plugins Imported.")

    async def boot(self) -> None:
        Config.TASK_MANAGER.loop = self.loop
        await super().start()

        LOGGER.info("Connected to TG.")

        await asyncio.to_thread(self._import)

        await Config.TASK_MANAGER.run_init_tasks()

        await self.log_text(text="<i>Started</i>")

        LOGGER.info("Idling...")
        self.is_idling = True

        await pyrogram.idle()

        await self.shut_down()

        LOGGER.info(f"\n\n{'#' * 10} END OF RUN {'#' * 10}\n\n", extra={"raw": True})

        sys.exit(self.exit_code)

    def raise_sigint(self) -> None:
        self.exit_code = 69
        signal.raise_signal(signal.SIGINT)

    async def shut_down(self) -> None:
        """Gracefully ShutDown all Processes"""
        LOGGER.info("Stopping all processes...")
        await Config.TASK_MANAGER.close_and_run_exit_tasks()
        await super().stop()
        LOGGER.info("Exiting...")
