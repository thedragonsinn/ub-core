import asyncio
import importlib
import json
import logging

from os import environ, path
from typing import Callable, Coroutine

from git import Repo

LOGGER = logging.getLogger("Config")


def update_extra_config():
    try:
        extra_config_path = Config.WORKING_DIR + ".extra_config"
        extra_config = importlib.import_module(extra_config_path)
        for key, val in vars(extra_config).items():
            if not key.startswith("_"):
                setattr(Config, key, val)
    except (ImportError, ModuleNotFoundError) as e:
        LOGGER.error(e)


class Cmd:
    def __init__(self, cmd: str, func: Callable, cmd_path: str, sudo: bool):
        self.cmd: str = cmd
        self.cmd_path: str = cmd_path
        self.dirname: str = path.basename(path.dirname(cmd_path))
        self.doc: str = func.__doc__ or "Not Documented."
        self.func: Callable = func
        self.loaded = False
        self.sudo: bool = sudo

    def __str__(self):
        return json.dumps(self.__dict__, indent=4, ensure_ascii=False, default=str)


class Config:
    BOT_NAME = "BOT"

    BACKGROUND_TASKS: list[asyncio.Task] = []

    CMD_DICT: dict[str, Cmd] = {}

    CMD_TRIGGER: str = environ.get("CMD_TRIGGER", ".")

    DEV_MODE: int = int(environ.get("DEV_MODE", 0))

    DISABLED_SUPERUSERS: list[int] = []

    INIT_TASKS: list[Coroutine] = []

    LOG_CHAT: int = int(environ.get("LOG_CHAT", 0))

    LOAD_HANDLERS: bool = True

    OWNER_ID: int = int(environ.get("OWNER_ID", 0))

    REPO: Repo = Repo(".")

    SUDO: bool = False

    SUDO_TRIGGER: str = environ.get("SUDO_TRIGGER", "!")

    SUDO_USERS: list[int] = []

    SUPERUSERS: list[int] = []

    UPSTREAM_REPO: str = ""

    UPDATE_REPO = "https://github.com/thedragonsinn/ub-core.git"

    WORKING_DIR = environ.get("WORKING_DIR", "app")


update_extra_config()
