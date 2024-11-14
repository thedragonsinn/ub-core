import asyncio
import importlib
import json
import logging
from os import environ, path, sep
from typing import Callable, Coroutine

from git import InvalidGitRepositoryError, Repo

LOGGER = logging.getLogger("Config")


def update_extra_config():
    """Update Config Attrs from the custom extra_config"""
    extra_config_path = Config.WORKING_DIR + ".extra_config"

    exc_name = extra_config_path.replace(".", sep) + ".py"
    if not path.isfile(exc_name):
        return

    extra_config = importlib.import_module(extra_config_path)

    for key, val in vars(extra_config).items():
        if not key.startswith("_"):
            setattr(Config, key, val)


class Cmd:
    def __init__(self, cmd: str, func: Callable, cmd_path: str, sudo: bool):
        self.cmd: str = cmd
        self.cmd_path: str = cmd_path
        self.dir_name: str = path.basename(path.dirname(cmd_path))
        self.doc: str = func.__doc__ or "Not Documented."
        self.func: Callable = func
        self.is_from_core: bool = "ub_core" in cmd_path
        self.loaded = False
        self.sudo: bool = sudo

    def __str__(self):
        return json.dumps(self.__dict__, indent=4, ensure_ascii=False, default=str)


class Config:
    BOT_NAME = environ.get("BOT_NAME", "BOT")

    BACKGROUND_TASKS: list[asyncio.Task] = []

    CMD_DICT: dict[str, Cmd] = {}

    CMD_TRIGGER: str = environ.get("CMD_TRIGGER", ".")

    DEV_MODE: int = int(environ.get("DEV_MODE", 0))

    DISABLED_SUPERUSERS: list[int] = []

    EXIT_TASKS: list[Callable] = []

    INIT_TASKS: list[Coroutine] = []

    INLINE_QUERY_CACHE: dict[str | int, dict] = {}

    LOG_CHAT: int = int(environ.get("LOG_CHAT", 0))

    LOAD_HANDLERS: bool = True

    MODE: str = "dual"

    OWNER_ID: int = int(environ.get("OWNER_ID", 0))

    try:
        REPO: Repo = Repo(".")
        EXIT_TASKS.append(REPO.close)
    except InvalidGitRepositoryError:
        REPO = None

    SUDO: bool = False

    SUDO_TRIGGER: str = environ.get("SUDO_TRIGGER", "!")

    SUDO_USERS: list[int] = []

    SUPERUSERS: list[int] = []

    UPSTREAM_REPO: str = environ.get("UPSTREAM_REPO", "")

    UPDATE_REPO = "https://github.com/thedragonsinn/ub-core"

    WORKING_DIR = environ.get("WORKING_DIR", "app")


update_extra_config()
