from ub_core.core.decorators.add_cmd import AddCmd
from ub_core.core.decorators.on_edited_message import OnEditedMessage
from ub_core.core.decorators.on_message import OnMessage


class CustomDecorators(AddCmd, OnMessage, OnEditedMessage): ...
