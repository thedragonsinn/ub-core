from .conversation import Conversation as Convo
from .db import CustomCollection, CustomDatabase, DATABASE_NAME, DB_URI
from .types import Message

if DB_URI:
    CustomDB = CustomDatabase(db_uri=DB_URI, db_name=DATABASE_NAME)
else:
    CustomDB = None
