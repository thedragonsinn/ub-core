import collections
import importlib
import json
import logging
import pathlib
import time
from os import getenv

from git import InvalidGitRepositoryError, Repo

from . import ub_core_dir
from .task_manager import TaskManager

LOGGER = logging.getLogger("Config")


def update_extra_config():
    """Update Config Attrs from the custom extra_config"""
    extra_config_path = Config.WORKING_DIR / "extra_config.py"

    if not extra_config_path.is_file():
        return

    py_path = extra_config_path.relative_to(Config.WORKING_DIR.parent)
    py_name = ".".join(py_path.with_suffix("").parts)
    extra_config = importlib.import_module(py_name)

    for key, val in vars(extra_config).items():
        if not key.startswith("_"):
            setattr(Config, key, val)


class Cmd:
    def __init__(self, cmd: str, func: collections.abc.Callable, path: str, allow_sudo: bool):
        self.cmd: str = cmd
        self.path: pathlib.Path = pathlib.Path(path)
        self.dir_name: str = self.path.parent.name
        self.doc: str = func.__doc__ or "Not Documented."
        self.func: collections.abc.Callable = func
        self.is_from_core: bool = self.path.is_relative_to(ub_core_dir)
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

    DOWNLOAD_PATH = pathlib.Path("downloads")

    DOWNLOAD_PATH.mkdir(exist_ok=True)

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

    TEMP_DOWNLOAD_PATH = lambda: Config.DOWNLOAD_PATH / str(time.time())

    UPSTREAM_REPO: str = getenv("UPSTREAM_REPO", "")

    UPDATE_REPO: str = "https://github.com/thedragonsinn/ub-core"

    WORKING_DIR: pathlib.Path = pathlib.Path(getenv("WORKING_DIR", "app")).resolve()


update_extra_config()
