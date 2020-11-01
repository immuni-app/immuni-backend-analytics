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
from immuni_common.core.config import MAX_ALLOWED_BUILD
from immuni_common.core.exceptions import SchemaValidationException
from immuni_common.models.enums import Platform
from tests.fixtures.operational_info import ANALYTICS_TOKEN, OPERATIONAL_INFO


@fixture
def headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {ANALYTICS_TOKEN}",
        "Immuni-Dummy-Data": "0",
        "Content-Type": "application/json; charset=utf-8",
    }


@mark.parametrize(
    "analytics_token",
    (
        "",
        "Bearer",
        f"Another {ANALYTICS_TOKEN}",
        "Bearer shorter",
        f"Bearer {ANALYTICS_TOKEN}longer",
        f"Bearer {ANALYTICS_TOKEN[:-1]}k",  # non-hexadecimal
        f"Bearer {ANALYTICS_TOKEN[:-1]}A",  # uppercase letter
    ),
)
async def test_apple_operational_info_malformed_analytics_token(
    client: TestClient,
    headers: Dict[str, str],
    operational_info: Dict[str, Any],
    analytics_token: str,
) -> None:
    headers["Authorization"] = analytics_token
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )
    assert response.status == SchemaValidationException.status_code
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 0


@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_with_exposure(
    redis_logger_info: MagicMock,
    client: TestClient,
    headers: Dict[str, str],
    operational_info: Dict[str, Any],
) -> None:
    # authorize the current token for the upload
    await managers.authorization_ios_redis.sadd(
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
            bluetooth_active=operational_info["bluetooth_active"],
            exposure_notification=operational_info["exposure_notification"],
            exposure_permission=operational_info["exposure_permission"],
            last_risky_exposure_on=date.fromisoformat(operational_info["last_risky_exposure_on"]),
            notification_permission=operational_info["notification_permission"],
            platform=Platform.IOS,
            province=operational_info["province"],
        ).to_dict()
    )

    assert not await managers.authorization_ios_redis.sismember(
        get_upload_authorization_member_for_current_month(with_exposure=True), ANALYTICS_TOKEN
    )

    redis_logger_info.assert_called_once_with("Successfully enqueued operational info.")


async def test_apple_operational_info_missing_redis_token(
    client: TestClient, headers: Dict[str, str], operational_info: Dict[str, Any]
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
    headers: Dict[str, str],
    operational_info: Dict[str, Any],
) -> None:
    assert OperationalInfo.objects.count() == 0
    operational_info["exposure_notification"] = 0

    # authorize the current token for the upload
    await managers.authorization_ios_redis.sadd(
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
            bluetooth_active=operational_info["bluetooth_active"],
            exposure_notification=operational_info["exposure_notification"],
            exposure_permission=operational_info["exposure_permission"],
            last_risky_exposure_on=None,
            notification_permission=operational_info["notification_permission"],
            platform=Platform.IOS,
            province=operational_info["province"],
        ).to_dict()
    )

    assert not await managers.authorization_ios_redis.sismember(
        get_upload_authorization_member_for_current_month(with_exposure=False), ANALYTICS_TOKEN
    )

    redis_logger_info.assert_called_once_with("Successfully enqueued operational info.")


@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_dummy(
    redis_logger_info: MagicMock,
    client: TestClient,
    headers: Dict[str, str],
    operational_info: Dict[str, Any],
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
@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_bad_request(
    redis_logger_info: MagicMock,
    bad_data: Dict[str, Any],
    client: TestClient,
    headers: Dict[str, str],
) -> None:
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=bad_data, headers=headers
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."

    assert OperationalInfo.objects.count() == 0
    redis_logger_info.assert_not_called()


@mark.parametrize(
    "bad_build", {None, 0, MAX_ALLOWED_BUILD + 1},
)
@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_bad_build(
    redis_logger_info: MagicMock,
    bad_build: Any,
    operational_info: Dict[str, Any],
    client: TestClient,
    headers: Dict[str, str],
) -> None:
    response = await client.post(
        "/v1/analytics/apple/operational-info",
        json=dict(**operational_info, build=bad_build),
        headers=headers,
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."

    assert OperationalInfo.objects.count() == 0
    redis_logger_info.assert_not_called()


@mark.parametrize(
    "build", range(1, MAX_ALLOWED_BUILD, MAX_ALLOWED_BUILD // 5),
)
@patch("immuni_analytics.helpers.redis._LOGGER.info")
async def test_apple_operational_info_good_build(
    redis_logger_info: MagicMock,
    build: Dict[str, Any],
    operational_info: Dict[str, Any],
    client: TestClient,
    headers: Dict[str, str],
) -> None:
    # authorize the current token for the upload
    await managers.authorization_ios_redis.sadd(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_current_month(with_exposure=True)
    )

    response = await client.post(
        "/v1/analytics/apple/operational-info",
        json=dict(**operational_info, build=build),
        headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert (
        json.loads(await managers.analytics_redis.lpop(config.OPERATIONAL_INFO_QUEUE_KEY))
        == OperationalInfo(
            bluetooth_active=operational_info["bluetooth_active"],
            exposure_notification=operational_info["exposure_notification"],
            exposure_permission=operational_info["exposure_permission"],
            last_risky_exposure_on=date.fromisoformat(operational_info["last_risky_exposure_on"]),
            notification_permission=operational_info["notification_permission"],
            platform=Platform.IOS,
            build=build,
            province=operational_info["province"],
        ).to_dict()
    )

    redis_logger_info.assert_called_once_with("Successfully enqueued operational info.")
