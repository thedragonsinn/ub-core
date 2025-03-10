import json
import os
from typing import Iterable

import dns.resolver
from motor.core import AgnosticClient, AgnosticCollection, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from ..config import Config

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8"]

DB_URI: str = os.environ.get("DB_URL", "").strip()
DATABASE_NAME = Config.BOT_NAME.lower().replace("-", "_")


class CustomCollection(AsyncIOMotorCollection):
    """A Custom Class with a few Extra Methods for ease of access"""

    def __init__(self, collection_name: str, database: AgnosticDatabase):
        super().__init__(database=database, name=collection_name)

    async def add_data(self: AgnosticCollection, data: dict) -> int | str:
        """
        Add or Update Existing Data

        Args:
            data: {"_id":id, rest of the data to be added/updated}

        Returns: Inserted Data ID if inserted else Modified Count

        Raises: KeyError if _id is not present in data.
        """
        unique_id_key = data.get("_id")

        if unique_id_key is None:
            # Thanks @kakashi_htk [TG] | @ashwinstr [GitHub] for raising error
            # suggestion.
            raise KeyError(
                f"Unique identifier key '_id' not found in "
                f"data:{json.dumps(data, indent=4, ensure_ascii=False, default=str)}"
            )

        is_existing_entry = await self.find_one({"_id": unique_id_key})

        if not is_existing_entry:
            entry: InsertOneResult = await self.insert_one(data)
            return entry.inserted_id
        else:
            entry: UpdateResult = await self.update_one(
                {"_id": data.pop("_id")}, {"$set": data}
            )
            return entry.modified_count

    async def delete_data(self: AgnosticCollection, id: int | str) -> int:
        """
        Delete a DB Collection Entry

        Args:
            id: collection_entry id

        Returns: Count of Number of Entries Deleted.

        """
        delete_result: DeleteResult = await self.delete_one({"_id": id})
        return delete_result.deleted_count

    async def increment(self: AgnosticCollection, id: int, key: str, count: int) -> int:
        """
        Increment a DB Entry Value for specified key.

        Args:
            id:  collection_entry id
            key: key to be incremented
            count: number to increment by

        Returns: Modified Count

        """
        increment_result = await self.update_one({"_id": id}, {"$inc": {key: count}})
        return increment_result.modified_count

    async def get_total(self: AgnosticCollection, keys: Iterable) -> list[dict]:
        """
        Get Sum for key's value across the Collection

        Args:
            keys: Keys to get total of

        Returns: [ {_id: None, key_name: total, key_name: total, ...} ]

        """
        data = {key: {"$sum": f"${key}"} for key in keys}
        pipeline = [{"$group": {"_id": None, **data}}]
        return [results async for results in self.aggregate(pipeline=pipeline)]


class CustomDatabase:
    def __init__(self, db_uri: str, db_name: str):
        self._client: AgnosticClient = AsyncIOMotorClient(db_uri)
        self._db: AgnosticDatabase = self._client[db_name]

        Config.EXIT_TASKS.append(self._client.close)

    def __getitem__(self, item: str) -> AgnosticCollection | CustomCollection:
        return CustomCollection(collection_name=item, database=self._db)

    def __call__(self, collection_name) -> AgnosticCollection | CustomCollection:
        return CustomCollection(collection_name=collection_name, database=self._db)
