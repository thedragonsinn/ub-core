from pyrogram.handlers import EditedMessageHandler, MessageHandler

# Thanks @Kakashi_htk [TG] | @ashwinstr [Github] for the basic concept.


class UnifiedHandler(MessageHandler, EditedMessageHandler):
    """
    A Custom Class to re-unify edited message support into single handler.
    Pyro V2 separated the two as OnMessage and OnEditedMessage.
    """
