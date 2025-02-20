from ub_core.core.decorators.add_cmd import AddCmd
from ub_core.core.decorators.on_edited_message import OnEditedMessage
from ub_core.core.decorators.on_message import OnMessage
from ub_core.core.decorators.make_async import MakeAsync


class CustomDecorators(AddCmd, MakeAsync, OnMessage, OnEditedMessage): ...
