import os
import tracemalloc

from dotenv import load_dotenv
from pathlib import Path

tracemalloc.start()

load_dotenv("config.env")


try:
    import uvloop  # NOQA
    # if uvloop is installed
    # set uvloop's loop as the default for this runtime.
    import asyncio
    asyncio.set_event_loop(uvloop.new_event_loop())
except (ImportError, ModuleNotFoundError):
    ...

ub_core_dir = Path(__file__).parent.resolve()

from .config import Cmd, Config
from .version import __version__
from .core import CustomCollection, CustomDatabase, Convo, CustomDB, Message
from .core.client import BOT

bot: BOT = BOT()

from .core.logging import LOGGER
