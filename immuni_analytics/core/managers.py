#    Copyright (C) 2020 Presidenza del Consiglio dei Ministri.
#    Please refer to the AUTHORS file for more information.
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Optional

import aioredis
from aioredis import Redis
from mongoengine import connect
from pymongo import MongoClient

from immuni_analytics.core import config
from immuni_common.core.managers import BaseManagers


class Managers(BaseManagers):
    """
    Collection of managers, lazily initialized.
    """

    _analytics_mongo: Optional[MongoClient] = None
    _analytics_redis: Optional[Redis] = None

    @property
    def analytics_mongo(self) -> MongoClient:
        """
        Return the MongoDB manager.
        """
        if self._analytics_mongo is None:
            raise RuntimeError("Cannot use MongoDB manager before initializing it.")
        return self._analytics_mongo

    @property
    def analytics_redis(self) -> Redis:
        """
        Retrieves the Analytics Redis Client. Raises an exception if it was not initialized.
        """
        if self._analytics_redis is None:
            raise RuntimeError("Attempting to use Analytics redis before initialization")
        return self._analytics_redis

    async def initialize(self, initialize_mongo: bool = False) -> None:
        """
        Initialize managers on demand.
        """
        await super().initialize()
        if initialize_mongo:
            self._analytics_mongo = connect(host=config.ANALYTICS_MONGO_URL)

        self._analytics_redis = await aioredis.create_redis_pool(
            address=config.ANALYTICS_BROKER_REDIS_URL, encoding="utf-8",
        )

    async def teardown(self) -> None:
        """
        Perform teardown actions (e.g., close open connections.)
        """
        await super().teardown()

        if self._analytics_mongo is not None:
            self._analytics_mongo.close()

        if self._analytics_redis is not None:
            self._analytics_redis.close()
            await self._analytics_redis.wait_closed()


managers = Managers()
