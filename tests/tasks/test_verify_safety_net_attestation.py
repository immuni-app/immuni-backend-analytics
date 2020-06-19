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

from typing import Any, Dict
from unittest.mock import MagicMock, patch

from immuni_analytics.celery.authorization.tasks.verify_safety_net_attestation import (
    _verify_safety_net_attestation,
)
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.safety_net import SafetyNetVerificationError, get_redis_key
from immuni_analytics.models.operational_info import OperationalInfo


@patch(
    "immuni_analytics.celery.authorization.tasks.verify_safety_net_attestation."
    "safety_net.verify_attestation",
    side_effect=SafetyNetVerificationError(),
)
async def test_verify_safety_net_attestation_verification_error(
    mock_verify_safety_net_attestation: MagicMock, operational_info: Dict[str, Any]
) -> None:
    await _verify_safety_net_attestation(
        "mock_safety_net_attestation",
        "mock_salt",
        OperationalInfo(**operational_info),
        "mock_last_risky_exposure_on",
    )

    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 0
    assert not await managers.analytics_redis.get(get_redis_key("mock_salt"))


@patch(
    "immuni_analytics.celery.authorization.tasks.verify_safety_net_attestation."
    "safety_net.verify_attestation",
    MagicMock(),
)
@patch("immuni_analytics.celery.authorization.tasks.verify_safety_net_attestation._LOGGER.warning")
async def test_verify_safety_net_attestation_used_salt(
    warning_logger: MagicMock, operational_info: Dict[str, Any]
) -> None:
    await managers.analytics_redis.set(get_redis_key("mock_salt"), 1)

    await _verify_safety_net_attestation(
        "mock_safety_net_attestation",
        "mock_salt",
        OperationalInfo(**operational_info),
        "mock_last_risky_exposure_on",
    )

    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 0
    warning_logger.assert_called_once_with(
        "Found previously used salt.",
        extra=dict(safety_net_attestation="mock_safety_net_attestation", salt="mock_salt"),
    )
