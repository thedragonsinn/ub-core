import os

import dns.resolver
from motor.core import AgnosticClient, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from ub_core.core import Str

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8"]

DB_URI: str = os.environ.get("DB_URL", "").strip()

if DB_URI:
    DB_CLIENT: AgnosticClient | None = AsyncIOMotorClient(DB_URI)
    DB: AgnosticDatabase | None = DB_CLIENT["plain_ub"]
else:
    DB_CLIENT = DB = None


class CustomDB(AsyncIOMotorCollection, Str):
    def __init__(self, collection_name: str):
        super().__init__(database=DB, name=collection_name)

    async def add_data(self, data: dict) -> None:
        """
        :param data: {"_id": db_id, rest of the data}
        entry is added or updated if exists.
        """
        found = await self.find_one({"_id": data["_id"]})
        if not found:
            await self.insert_one(data)
        else:
            await self.update_one({"_id": data.pop("_id")}, {"$set": data})

    async def delete_data(self, id: int | str) -> bool | None:
        """
        :param id: the db id key to delete.
        :return: True if entry was deleted.
        """
        found = await self.find_one({"_id": id})
        if found:
            await self.delete_one({"_id": id})
            return True
