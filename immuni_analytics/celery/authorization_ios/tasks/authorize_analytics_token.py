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

import asyncio
import logging
import random
from datetime import timedelta

from immuni_analytics.celery.authorization_ios.app import celery_app
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.device_check import (
    DeviceCheckApiError,
    fetch_device_check_bits,
    set_device_check_bits,
)
from immuni_analytics.helpers.redis import get_all_authorizations_for_upload
from immuni_analytics.monitoring.celery import (
    AUTHORIZE_ANALYTICS_TOKEN_AUTHORIZED,
    AUTHORIZE_ANALYTICS_TOKEN_BLACKLISTED,
    AUTHORIZE_ANALYTICS_TOKEN_FIRST_STEP_BEGIN,
    AUTHORIZE_ANALYTICS_TOKEN_SECOND_STEP_BEGIN,
    AUTHORIZE_ANALYTICS_TOKEN_THIRD_STEP_BEGIN,
)
from immuni_common.core.exceptions import ImmuniException
from immuni_common.models.enums import Environment

_LOGGER = logging.getLogger(__name__)


class DiscardAnalyticsTokenException(ImmuniException):
    """
    Raised when the device cannot authorize an analytics token.
    """


class BlacklistDeviceException(ImmuniException):
    """
    Raised when a device is attempting to validate multiple tokens.
    """


@celery_app.task()
def authorize_analytics_token(analytics_token: str, device_token: str) -> None:  # pragma: no cover
    """
    Celery doesn't support async functions, so we wrap it around asyncio.run.
    """
    asyncio.run(_authorize_analytics_token(analytics_token, device_token))


async def _authorize_analytics_token(analytics_token: str, device_token: str) -> None:
    """
    Check if the device token comes from a genuine device that is not sending concurrent calls.
    If there are no anomalies, authorize the analytics token to perform operational info uploads.

    :param analytics_token: the analytics token to authorize.
    :param device_token: the device token to check against the DeviceCheck API.
    """
    # NOTE: bandit complains about using random.uniform stating "[B311:blacklist] Standard
    #  pseudo-random generators are not suitable for security/cryptographic purposes.".
    #  The "waiting for a random time" is not a security/cryptographic action, thus the issue is
    #  intentionally waived.
    try:
        await _first_step(device_token)
        await asyncio.sleep(
            random.uniform(config.CHECK_TIME_SECONDS_MIN, config.CHECK_TIME_SECONDS_MAX)  # nosec
        )
        await _second_step(device_token)
        await asyncio.sleep(
            random.uniform(config.READ_TIME_SECONDS_MIN, config.READ_TIME_SECONDS_MAX)  # nosec
        )
        await _third_step(device_token)

    except BlacklistDeviceException:
        await _blacklist_device(device_token)
        return

    except (DiscardAnalyticsTokenException, DeviceCheckApiError):
        return

    await _add_analytics_token_to_redis(analytics_token)


async def _first_step(device_token: str) -> None:
    """
    Fetch the DeviceCheck bits and ensure the bit configuration is the expected one.
    If not, blacklist the device.

    :raises:
      BlacklistDeviceException: if an anomaly is detected
      DiscardAnalyticsTokenException: if the token has already been used in the current month.
    """
    AUTHORIZE_ANALYTICS_TOKEN_FIRST_STEP_BEGIN.inc()
    device_check_data = await fetch_device_check_bits(device_token)

    # Do not perform this check if we are not in release environment otherwise we can use a
    # developer device only once a month.
    if config.ENV == Environment.RELEASE and device_check_data.used_in_current_month:
        _LOGGER.warning(
            "Detected device that already authorized an analytics_token in the current month.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
        raise DiscardAnalyticsTokenException()

    if not device_check_data.is_default_configuration:
        _LOGGER.warning(
            "Found token that is not compliant with the default configuration in the first step.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
        raise BlacklistDeviceException()


async def _second_step(device_token: str) -> None:
    """
    Fetch the DeviceCheck bits and ensure the bit configuration is the expected one.
    If it is, set the bits to (False, True) and return.
    If not, blacklist the device.

    :raises: BlacklistDeviceException if an anomaly is detected.
    """
    AUTHORIZE_ANALYTICS_TOKEN_SECOND_STEP_BEGIN.inc()
    device_check_data = await fetch_device_check_bits(device_token)
    if not device_check_data.is_default_configuration:
        _LOGGER.warning(
            "Found token that is not compliant with the default configuration in the second step.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
        raise BlacklistDeviceException()

    await set_device_check_bits(device_token, bit0=True, bit1=False)


async def _third_step(device_token: str) -> None:
    """
    Fetch the DeviceCheck bits and ensure the bit configuration is the expected one.
    If it is, set the bits to (False, False) and return.
    If not, blacklist the device.

    :raises: BlacklistDeviceException if an anomaly is detected.
    """
    AUTHORIZE_ANALYTICS_TOKEN_THIRD_STEP_BEGIN.inc()
    device_check_data = await fetch_device_check_bits(device_token)
    if not device_check_data.is_authorized:
        _LOGGER.warning(
            "Found token that is not authorized in the third step.",
            extra=dict(
                env=config.ENV.value,
                bit0=device_check_data.bit0,
                bit1=device_check_data.bit1,
                last_update_time=device_check_data.last_update_time,
            ),
        )
        raise BlacklistDeviceException()

    await set_device_check_bits(device_token, bit0=False, bit1=False)


async def _blacklist_device(device_token: str) -> None:
    """
    Set both DeviceCheck bits to True, a configuration that indicates the device is blacklisted
    and cannot send analytics anymore.

    :param device_token: the device token of the device to blacklist.
    """
    # NOTE: To avoid manually unlocking developers devices, perform blacklisting only within the
    #  release environment.
    if config.ENV == Environment.RELEASE:
        await set_device_check_bits(device_token, bit0=True, bit1=True)
    AUTHORIZE_ANALYTICS_TOKEN_BLACKLISTED.inc()


async def _add_analytics_token_to_redis(analytics_token: str) -> None:
    """
    Add the values needed to update operational info for the current and the next month to the set
    associated with the analytics token.

    :param analytics_token: the analytics token to authorize for upload.
    """
    pipe = managers.analytics_redis.pipeline()
    pipe.sadd(analytics_token, *get_all_authorizations_for_upload())
    pipe.expire(
        analytics_token, timedelta(days=config.ANALYTICS_TOKEN_EXPIRATION_DAYS).total_seconds()
    )
    await pipe.execute()
    _LOGGER.info("New authorized analytics token.", extra=dict(analytics_token=analytics_token))
    AUTHORIZE_ANALYTICS_TOKEN_AUTHORIZED.inc()
