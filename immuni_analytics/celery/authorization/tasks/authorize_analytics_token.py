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
import logging
import random

from immuni_analytics.celery.authorization.app import celery_app
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.device_check import fetch_device_check_bits, set_device_check_bits
from immuni_analytics.helpers.redis import (
    get_authorized_tokens_redis_key_current_month,
    get_authorized_tokens_redis_key_next_month,
)
from immuni_common.core.exceptions import ImmuniException
from immuni_common.models.enums import Environment

_LOGGER = logging.getLogger(__name__)


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
        # NOTE: bandit complains about using random.uniform stating "[B311:blacklist] Standard
        #  pseudo-random generators are not suitable for security/cryptographic purposes.".
        #  The "waiting for a random time" is not a security/cryptographic action, thus the issue is
        #  intentionally waived.
        await _first_step(device_token)
        await asyncio.sleep(random.uniform(1, config.CHECK_TIME))  # nosec
        await _second_step(device_token)
        await asyncio.sleep(random.uniform(1, config.READ_TIME))  # nosec
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
    if config.ENV == Environment.RELEASE and device_check_data.used_in_current_month:
        _LOGGER.warning(
            "Found token already used in current month",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
        raise DiscardAnalyticsTokenException()

    if not device_check_data.is_default_configuration_compliant:
        _LOGGER.warning(
            "Found token not default configuration compliant in first step.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
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
        _LOGGER.warning(
            "Found token not default configuration compliant in second step.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
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
        _LOGGER.warning(
            "Found token not authorization configuration compliant in third step.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
        await _blacklist_device(device_token)

    await set_device_check_bits(device_token, bit0=False, bit1=False)


async def _blacklist_device(device_token: str) -> None:
    """
    Set the both DeviceCheck bits to True, a configuration that marks blacklisted devices.

    :raises: DiscardAnalyticsTokenException
    """
    if config.ENV == Environment.RELEASE:
        await set_device_check_bits(device_token, bit0=True, bit1=True)

    raise DiscardAnalyticsTokenException()


async def _add_analytics_token_to_redis(analytics_token: str) -> None:
    """
    Add the analytics token to the sets corresponding to the current and the next months.
    """
    pipe = managers.analytics_redis.pipeline()
    pipe.sadd(get_authorized_tokens_redis_key_current_month(with_exposure=True), analytics_token)
    pipe.sadd(get_authorized_tokens_redis_key_current_month(with_exposure=False), analytics_token)
    pipe.sadd(get_authorized_tokens_redis_key_next_month(with_exposure=True), analytics_token)
    pipe.sadd(get_authorized_tokens_redis_key_next_month(with_exposure=False), analytics_token)
    await pipe.execute()
