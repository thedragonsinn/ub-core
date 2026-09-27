import tracemalloc
from pathlib import Path

from dotenv import load_dotenv

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

ub_core_dir = Path(__file__).parent

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

from .core.logging import LOGGER
