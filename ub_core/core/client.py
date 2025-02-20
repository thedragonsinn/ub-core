import asyncio
import glob
import importlib
import logging
import os
import sys
from functools import cached_property
from inspect import iscoroutine, iscoroutinefunction
from signal import SIGINT, raise_signal

from pyrogram import Client, idle

from ub_core import ub_core_dir_name

from .conversation import Conversation as Convo
from .decorators import CustomDecorators
from .methods import Methods
from ..config import Config

LOGGER = logging.getLogger(Config.BOT_NAME)


def import_modules(dir_name):
    """Import Plugins and Append init_task to Config.INIT_TASK"""
    plugins_dir = os.path.join(dir_name, "**/[!^_]*.py")
    modules = glob.glob(pathname=plugins_dir, recursive=True)

    if dir_name == ub_core_dir_name:
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
        import_modules(ub_core_dir_name)
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

        LOGGER.info("Connected to TG.")

        await asyncio.to_thread(self._import)

        await self._run_init_tasks()

        await self.log_text(text="<i>Started</i>")

        LOGGER.info("Idling...")
        self.is_idling = True

        await idle()

        await self.shut_down()
        sys.exit(self.exit_code)

    def raise_sigint(self) -> None:
        self.exit_code = 69
        raise_signal(SIGINT)

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

        await super().stop()

        LOGGER.info("Exit Tasks Completed. Exiting...")
