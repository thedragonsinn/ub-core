from pyrogram.filters import create

from .dispatcher import cmd_dispatcher

valid_chat_filter = create(lambda _, __, message: bool(message.chat))
