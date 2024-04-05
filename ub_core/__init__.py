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

# fmt:off

from ub_core.config import Cmd, Config
from ub_core.core import DB, DB_CLIENT, Convo, CustomDB, Message
from ub_core.core.client import BOT

bot: BOT = BOT()

from ub_core.core.logger import LOGGER
from ub_core.version import __version__

# fmt: on
