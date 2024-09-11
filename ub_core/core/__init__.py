# fmt: off

import json


class Str:
    def __str__(self):
        return json.dumps(self.__dict__, indent=4, ensure_ascii=False, default=str)


from ub_core.core.conversation import Conversation as Convo
from ub_core.core.db import DB, DB_CLIENT, CustomDB
from ub_core.core.types.callback_query import CallbackQuery
from ub_core.core.types.message import Message
