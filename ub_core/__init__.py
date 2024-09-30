import os
import tracemalloc

from dotenv import load_dotenv

tracemalloc.start()

load_dotenv("config.env")


try:
    import uvloop

    uvloop.install()
except (ImportError, ModuleNotFoundError):
    ...

ub_core_dir_name = os.path.dirname(__file__)

from .config import Cmd, Config
from .version import __version__
from .core import DB, DB_CLIENT, Convo, CustomDB, Message
from .core.client import BOT

bot: BOT = BOT()

from .core.logger import LOGGER
