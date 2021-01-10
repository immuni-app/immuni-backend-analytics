#  Copyright (C) 2020 Presidenza del Consiglio dei Ministri.
#  Please refer to the AUTHORS file for more information.
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU Affero General Public License for more details.
#  You should have received a copy of the GNU Affero General Public License
#  along with this program. If not, see <https://www.gnu.org/licenses/>.

from asyncio import AbstractEventLoop
from contextlib import contextmanager
from typing import Any, Awaitable, Callable, Iterator

from celery import Celery
from mongoengine import get_db
from pytest import fixture
from pytest_sanic.utils import TestClient
from sanic import Sanic

from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_common.helpers.tests import create_no_expired_keys_fixture


@contextmanager
def config_set(name: str, value: Any) -> Iterator[None]:
    old_value = getattr(config, name)
    setattr(config, name, value)
    try:
        yield
    finally:
        setattr(config, name, old_value)


@fixture(autouse=True)
async def cleanup(sanic: Sanic) -> None:
    managers.analytics_mongo.drop_database(get_db().name)
    await managers.analytics_redis.flushdb()
    await managers.authorization_ios_redis.flushdb()
    await managers.authorization_android_redis.flushdb()
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


@fixture(scope="function")
def setup_exposure_payload_celery_app(monitoring_setup: None) -> Celery:
    from immuni_analytics.celery.scheduled.app import celery_app

    celery_app.conf.update(CELERY_ALWAYS_EAGER=True)
    return celery_app


@fixture(autouse=True)
def ensure_no_unexpired_keys(sanic: Sanic) -> None:
    create_no_expired_keys_fixture(managers.analytics_redis)
