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
from asyncio import AbstractEventLoop
from typing import AsyncGenerator, Awaitable, Callable

from mongoengine import get_db
from pytest import fixture
from pytest_sanic.utils import TestClient
from sanic import Sanic

from immuni_analytics.core.managers import managers


@fixture(autouse=True)
async def cleanup(sanic: Sanic) -> None:
    managers.analytics_mongo.drop_database(get_db().name)
    await managers.analytics_redis.flushdb()
    pass


@fixture
async def sanic(monitoring_setup: None) -> Sanic:
    from immuni_analytics.sanic import sanic_app

    await managers.initialize(initialize_mongo=True)
    yield sanic_app
    await managers.teardown()


@fixture
async def sanic_custom_client(sanic_client: TestClient) -> TestClient:
    yield sanic_client


@fixture
def client(
    loop: AbstractEventLoop,
    sanic: Sanic,
    sanic_custom_client: Callable[[Sanic], Awaitable[TestClient]],
) -> TestClient:
    return loop.run_until_complete(sanic_custom_client(sanic))
