from pyrogram.enums import ChatType
from pyrogram.types import Message

from ub_core import BOT, bot

from ..handlers import UnifiedHandler, cmd_dispatcher, create, valid_chat_filter
from ...config import Cmd, Config


def client_check(_, client: BOT, message: Message):
    if message.chat and message.chat.type == ChatType.PRIVATE:
        return Config.MODE != "bot" or client.is_bot
    if Config.MODE == "bot":
        return client.is_bot
    return True


def check_sudo_access(cmd_obj: Cmd):
    in_loaded = cmd_obj.loaded
    has_access = cmd_obj.sudo
    return in_loaded and has_access


def cmd_check(message: Message, trigger: str, sudo: bool = False) -> bool:
    """
    Check if first word of message is a valid cmd \n
    if sudo: check if sudo users have access to the cmd.
    """
    start_str = message.text.split(maxsplit=1)[0]
    cmd = start_str.replace(trigger, "", 1)
    cmd_obj = Config.CMD_DICT.get(cmd)
    if not cmd_obj:
        return False
    if sudo:
        return check_sudo_access(cmd_obj)
    return True


def basic_check(message: Message):
    return not message.chat or not message.text or not message.from_user


def owner_check(_, __, message: Message) -> bool:
    """Check if Message is from the Owner"""
    if (
        basic_check(message)
        or not message.text.startswith(Config.CMD_TRIGGER)
        or message.from_user.id != Config.OWNER_ID
        or (message.chat.id != Config.OWNER_ID and not message.outgoing)
    ):
        return False
    return cmd_check(message, Config.CMD_TRIGGER)


def owner_sudo_check(_, client: BOT, message: Message):
    if (
        basic_check(message)
        or not message.text.startswith(Config.SUDO_TRIGGER)
        or message.from_user.id != Config.OWNER_ID
        or client.is_user
    ):
        return False
    return cmd_check(message, Config.SUDO_TRIGGER)


def sudo_check(_, __, message: Message) -> bool:
    """Check if Message is from a Sudo User"""
    if (
        not Config.SUDO
        or basic_check(message)
        or not message.text.startswith(Config.SUDO_TRIGGER)
        or message.from_user.id not in Config.SUDO_USERS
    ):
        return False
    return cmd_check(message, Config.SUDO_TRIGGER, sudo=True)


def super_user_check(_, __, message: Message):
    """Check if Message is from a Super User"""
    if (
        basic_check(message)
        or not message.text.startswith(Config.SUDO_TRIGGER)
        or message.from_user.id not in Config.SUPERUSERS
        or message.from_user.id in Config.DISABLED_SUPERUSERS
    ):
        return False
    return cmd_check(message, Config.SUDO_TRIGGER)


CMD_FILTER = valid_chat_filter & (
    create(owner_check)
    | create(owner_sudo_check)
    | (create(client_check) & (create(sudo_check) | create(super_user_check)))
)

# Don't Load Handler if Value is not True
# Useful for Legacy non-db type bots or
# Bots who would like to use custom filters
# for those, Manually add handler on the cmd_dispatcher

if Config.LOAD_HANDLERS:
    bot.add_handler(UnifiedHandler(callback=cmd_dispatcher, filters=CMD_FILTER), group=1)
    if bot.has_bot:
        bot.bot.add_handler(UnifiedHandler(callback=cmd_dispatcher, filters=CMD_FILTER), group=1)
