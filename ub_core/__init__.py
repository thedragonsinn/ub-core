import os
import tracemalloc

from dotenv import load_dotenv

tracemalloc.start()

load_dotenv("config.env")


try:
    import uvloop  # NOQA

    uvloop.install()
except (ImportError, ModuleNotFoundError):
    ...

ub_core_dirname = os.path.dirname(__file__)

from .config import Cmd, Config
from .core import (
    CallbackQuery,
    Convo,
    CustomCollection,
    CustomDatabase,
    CustomDB,
    InlineResult,
    Message,
)
from .core.client import DualClient
from .version import __version__

bot: DualClient = DualClient()
BOT = DualClient

from .core.logger import LOGGER
