import collections
import importlib
import json
import logging
from os import getenv, path, sep

from git import InvalidGitRepositoryError, Repo

from .task_manager import TaskManager

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
    def __init__(self, cmd: str, func: collections.abc.Callable, cmd_path: str, allow_sudo: bool):
        self.cmd: str = cmd
        self.cmd_path: str = cmd_path
        self.dir_name: str = path.basename(path.dirname(cmd_path))
        self.doc: str = func.__doc__ or "Not Documented."
        self.func: collections.abc.Callable = func
        self.is_from_core: bool = "ub_core" in cmd_path
        self.loaded_for_sudo = False
        self.allow_sudo: bool = allow_sudo

    def __str__(self):
        return json.dumps(self.__dict__, indent=4, ensure_ascii=False, default=str)


class Config:
    TASK_MANAGER: TaskManager = TaskManager()

    BOT_NAME = getenv("BOT_NAME", "BOT")

    CMD_DICT: dict[str, Cmd] = {}

    CMD_TRIGGER: str = getenv("CMD_TRIGGER", ".")

    COMMAND_LOG_LEVEL: int = int(getenv("COMMAND_LOG_LEVEL", 0))

    DEV_MODE: int = int(getenv("DEV_MODE", 0))

    DISABLED_SUPERUSERS: set[int] = set()

    INLINE_QUERY_CACHE: dict[str | int, dict] = {}

    INLINE_RESULT_CACHE: set[str] = set()

    LOG_CHAT: int = int(getenv("LOG_CHAT", 0))

    LOG_CHAT_THREAD_ID: int = int(getenv("LOG_CHAT_THREAD_ID", 0)) or None

    LOAD_HANDLERS: bool = True

    OWNER_ID: int = int(getenv("OWNER_ID", 0))

    try:
        REPO: Repo = Repo(".")
        TASK_MANAGER.add_exit(REPO.close)
    except InvalidGitRepositoryError:
        REPO = None

    SUDO: bool = False

    SUDO_TRIGGER: str = getenv("SUDO_TRIGGER", "!")

    SUDO_USERS: set[int] = set()

    SUPERUSERS: set[int] = set()

    UPSTREAM_REPO: str = getenv("UPSTREAM_REPO", "")

    UPDATE_REPO: str = "https://github.com/thedragonsinn/ub-core"

    WORKING_DIR: str = getenv("WORKING_DIR", "app")


update_extra_config()
