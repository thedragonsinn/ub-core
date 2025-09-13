import base64
import logging
import struct
from pathlib import Path

from pyrogram.storage import FileStorage as FS

from ..config import Config

LOGGER = logging.getLogger(Config.BOT_NAME)


class FileStorage(FS):
    def __init__(self, name: str, session_string: str = None, workdir: Path = Path(".")):
        super().__init__(name=name, workdir=Path(workdir))
        if isinstance(session_string, str):
            session_string = session_string.strip()
        self.session_string = session_string

    async def open(self):
        await super().open()

        if not self.session_string:
            return

        string_len = len(self.session_string)
        b64_string = base64.urlsafe_b64decode(self.session_string + "=" * (-string_len % 4))

        # Old format
        if string_len in [
            self.SESSION_STRING_SIZE,
            self.SESSION_STRING_SIZE_64,
        ]:
            if string_len == self.SESSION_STRING_SIZE:
                format = self.OLD_SESSION_STRING_FORMAT
            else:
                format = self.OLD_SESSION_STRING_FORMAT_64

            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(format, b64_string)

            await self.dc_id(dc_id)
            await self.test_mode(test_mode)
            await self.auth_key(auth_key)
            await self.user_id(user_id)
            await self.is_bot(is_bot)
            await self.date(0)

            LOGGER.warning(
                "You are using an old session string format. Use export_session_string to update"
            )
            return

        dc_id, api_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
            self.SESSION_STRING_FORMAT, b64_string
        )

        await self.dc_id(dc_id)
        await self.api_id(api_id)
        await self.test_mode(test_mode)
        await self.auth_key(auth_key)
        await self.user_id(user_id)
        await self.is_bot(is_bot)
        await self.date(0)
