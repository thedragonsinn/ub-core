import os
import tracemalloc

from dotenv import load_dotenv
from pathlib import Path

tracemalloc.start()

load_dotenv("config.env")


try:
    import uvloop

    uvloop.install()
except (ImportError, ModuleNotFoundError):
    ...

ub_core_dir = Path(__file__).parent.resolve()

from .config import Cmd, Config
from .version import __version__
from .core import CustomCollection, CustomDatabase, Convo, CustomDB, Message
from .core.client import BOT

bot: BOT = BOT()

from .core.logging import LOGGER
