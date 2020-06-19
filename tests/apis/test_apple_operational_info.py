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

import json
from datetime import date
from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from pytest import fixture, mark
from pytest_sanic.utils import TestClient

from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.redis import get_upload_authorization_member_for_current_month
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform
from tests.fixtures.operational_info import OPERATIONAL_INFO

ANALYTICS_TOKEN = (
    "0a17753fecc38a5e259319e4524b55df439a98c1ff6326df7247263aa1192701cbe8799457cb1ac173590"
    "eecb11bfe62a34cc0798f95d8842124814c24f53ff"
)


@fixture
def headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {ANALYTICS_TOKEN}",
        "Immuni-Dummy-Data": "0",
        "Content-Type": "application/json; charset=utf-8",
    }


@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_with_exposure(
    redis_logger_info: MagicMock,
    client: TestClient,
    operational_info: Dict[str, Any],
    headers: Dict[str, str],
) -> None:
    # authorize the current token for the upload
    await managers.analytics_redis.sadd(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_current_month(with_exposure=True)
    )

    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 1
    assert (
        json.loads(await managers.analytics_redis.lpop(config.OPERATIONAL_INFO_QUEUE_KEY))
        == OperationalInfo(
            platform=Platform.IOS,
            province=operational_info["province"],
            exposure_permission=operational_info["exposure_permission"],
            bluetooth_active=operational_info["bluetooth_active"],
            notification_permission=operational_info["notification_permission"],
            exposure_notification=operational_info["exposure_notification"],
            last_risky_exposure_on=date.fromisoformat(operational_info["last_risky_exposure_on"]),
        ).to_dict()
    )

    assert not await managers.analytics_redis.sismember(
        get_upload_authorization_member_for_current_month(with_exposure=True), ANALYTICS_TOKEN
    )

    redis_logger_info.assert_called_once_with("Successfully enqueued operational info.")


async def test_apple_operational_info_missing_token(
    client: TestClient, operational_info: Dict[str, Any], headers: Dict[str, str]
) -> None:
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )
    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 0


@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_without_exposure(
    redis_logger_info: MagicMock,
    client: TestClient,
    operational_info: Dict[str, Any],
    headers: Dict[str, str],
) -> None:
    assert OperationalInfo.objects.count() == 0
    operational_info["exposure_notification"] = 0

    # authorize the current token for the upload
    await managers.analytics_redis.sadd(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_current_month(with_exposure=False)
    )

    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 1
    assert (
        json.loads(await managers.analytics_redis.lpop(config.OPERATIONAL_INFO_QUEUE_KEY))
        == OperationalInfo(
            platform=Platform.IOS,
            province=operational_info["province"],
            exposure_permission=operational_info["exposure_permission"],
            bluetooth_active=operational_info["bluetooth_active"],
            notification_permission=operational_info["notification_permission"],
            exposure_notification=operational_info["exposure_notification"],
            last_risky_exposure_on=None,
        ).to_dict()
    )

    assert not await managers.analytics_redis.sismember(
        get_upload_authorization_member_for_current_month(with_exposure=False), ANALYTICS_TOKEN
    )

    redis_logger_info.assert_called_once_with("Successfully enqueued operational info.")


@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_dummy(
    redis_logger_info: MagicMock,
    client: TestClient,
    operational_info: Dict[str, Any],
    headers: Dict[str, str],
) -> None:
    headers["Immuni-Dummy-Data"] = "1"
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 0

    redis_logger_info.assert_not_called()


@mark.parametrize(
    "bad_data",
    [{k: v for k, v in OPERATIONAL_INFO.items() if k != excluded} for excluded in OPERATIONAL_INFO],
)
async def test_apple_operational_info_bad_request(
    client: TestClient, bad_data: Dict[str, Any], headers: Dict[str, str]
) -> None:
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=bad_data, headers=headers
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."

    assert OperationalInfo.objects.count() == 0
