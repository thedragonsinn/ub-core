from pyrogram.filters import create

from .dispatcher import cmd_dispatcher
from .unified_message_handler import UnifiedHandler

valid_chat_filter = create(lambda _, __, message: bool(message.chat))
