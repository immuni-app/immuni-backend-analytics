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
from typing import Any, Dict

from aioredis.commands.string import StringCommandsMixin

from immuni_analytics.celery.authorization.app import celery_app
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers import safety_net
from immuni_analytics.helpers.redis import enqueue_operational_info
from immuni_analytics.helpers.safety_net import SafetyNetVerificationError
from immuni_analytics.models.operational_info import OperationalInfo

_LOGGER = logging.getLogger(__name__)


@celery_app.task()
def verify_safety_net_attestation(
    safety_net_attestation: str,
    salt: str,
    operational_info: Dict[str, Any],
    last_risky_exposure_on: str,
) -> None:  # pragma: no cover
    """
    Celery doesn't support async functions, so we wrap it around asyncio.run.
    """
    asyncio.run(
        _verify_safety_net_attestation(
            safety_net_attestation,
            salt,
            OperationalInfo.from_dict(operational_info),
            last_risky_exposure_on,
        )
    )


async def _verify_safety_net_attestation(
    safety_net_attestation: str,
    salt: str,
    operational_info: OperationalInfo,
    last_risky_exposure_on: str,
) -> None:
    """
    Verify that the safety_net_attestation is genuine. Prevent race conditions and save the
    operational_info.

    :param safety_net_attestation: the SafetyNet attestation to validate.
    :param salt: the salt sent in the request.
    :param operational_info: the device operational information.
    :param last_risky_exposure_on: the last risky exposure isoformat date.
    """
    try:
        safety_net.verify_attestation(
            safety_net_attestation, salt, operational_info, last_risky_exposure_on
        )
    except SafetyNetVerificationError:
        return

    # this salt cannot be used for the next SAFETY_NET_MAX_SKEW_MINUTES
    if await managers.analytics_redis.set(
        key=safety_net.get_redis_key(salt),
        value=1,
        expire=config.SAFETY_NET_MAX_SKEW_MINUTES * 60,
        exist=StringCommandsMixin.SET_IF_NOT_EXIST,
    ):
        await enqueue_operational_info(operational_info)
    else:
        _LOGGER.warning(
            "Found previously used salt.",
            extra=dict(safety_net_attestation=safety_net_attestation, salt=salt),
        )
