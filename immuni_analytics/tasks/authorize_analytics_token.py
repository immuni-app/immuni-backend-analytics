#   Copyright (C) 2020 Presidenza del Consiglio dei Ministri.
#   Please refer to the AUTHORS file for more information.
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#   You should have received a copy of the GNU Affero General Public License
#   along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio

from immuni_analytics.celery import celery_app
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.device_check import fetch_device_check_bits, set_device_check_bits
from immuni_analytics.helpers.redis import (
    get_authorized_tokens_redis_key_current_month,
    get_authorized_tokens_redis_key_next_month,
)
from immuni_common.core.exceptions import ImmuniException


class DiscardAnalyticsTokenException(ImmuniException):
    """Raised when the device cannot authorize an analytics token."""


@celery_app.task()
def authorize_analytics_token(analytics_token: str, device_token: str) -> None:  # pragma: no cover
    """
     Celery doesn't support async functions, so we wrap it around asyncio.run.
     """
    asyncio.run(_authorize_analytics_token(analytics_token, device_token))


async def _authorize_analytics_token(analytics_token: str, device_token: str) -> None:
    try:
        # TODO wait time between one step and the next one
        await _first_step(device_token)
        await _second_step(device_token)
        await _third_step(device_token)
    except DiscardAnalyticsTokenException:
        return

    await _add_analytics_token_to_redis(analytics_token)


async def _first_step(device_token: str) -> None:
    """
    Fetch the DeviceCheck bits and ensure the configuration is expected.
    If not, blacklist the device.

    :raises: DiscardAnalyticsTokenException
    """
    device_check_data = await fetch_device_check_bits(device_token)
    if not device_check_data.is_default_configuration_compliant:
        # TODO check if we always need to blacklist here
        await _blacklist_device(device_token)


async def _second_step(device_token: str) -> None:
    """
    Fetch the DeviceCheck bits and ensure the configuration is expected.
    If it is, set the bits to (0,1) and return.
    If not, blacklist the device.

    :raises: DiscardAnalyticsTokenException
    """
    device_check_data = await fetch_device_check_bits(device_token)
    if not device_check_data.is_default_configuration_compliant:
        await _blacklist_device(device_token)

    await set_device_check_bits(device_token, bit0=True, bit1=False)


async def _third_step(device_token: str) -> None:
    """
    Fetch the DeviceCheck bits and ensure the configuration is expected.
    If it is, set the bits to (0,0) and return.
    If not, blacklist the device.

    :raises: DiscardAnalyticsTokenException
    """
    device_check_data = await fetch_device_check_bits(device_token)
    if not device_check_data.is_authorized_configuration_compliant:
        await _blacklist_device(device_token)

    await set_device_check_bits(device_token, bit0=False, bit1=False)


async def _blacklist_device(device_token: str) -> None:
    """
    Set the both DeviceCheck bits to True, a configuration that marks blacklisted devices.

    :raises: DiscardAnalyticsTokenException
    """
    await set_device_check_bits(device_token, bit0=True, bit1=True)
    raise DiscardAnalyticsTokenException()


async def _add_analytics_token_to_redis(analytics_token: str) -> None:
    """
    Add the analytics token to the sets corresponding to the current and the next months.
    """
    pipe = managers.analytics_redis.pipeline()
    pipe.analytics_redis.sadd(
        get_authorized_tokens_redis_key_current_month(with_exposure=True), analytics_token
    )
    pipe.analytics_redis.sadd(
        get_authorized_tokens_redis_key_current_month(with_exposure=False), analytics_token
    )
    pipe.analytics_redis.sadd(
        get_authorized_tokens_redis_key_next_month(with_exposure=True), analytics_token
    )
    pipe.analytics_redis.sadd(
        get_authorized_tokens_redis_key_next_month(with_exposure=False), analytics_token
    )
    await pipe.execute()
