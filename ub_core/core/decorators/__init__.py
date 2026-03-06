from .add_cmd import AddCmd
from .make_async import MakeAsync
from .on_callback_query import OnCallbackQuery
from .on_edited_message import OnEditedMessage
from .on_message import OnMessage
from .register_tasks import RegisterTask
from .register_worker import RegisterWorker


class CustomDecorators(
    AddCmd,
    MakeAsync,
    OnMessage,
    OnEditedMessage,
    OnCallbackQuery,
    RegisterTask,
    RegisterWorker,
): ...
