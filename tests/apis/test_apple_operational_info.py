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
from copy import deepcopy
from datetime import date
from http import HTTPStatus
from typing import Any, Dict

from pytest import fixture, mark
from pytest_sanic.utils import TestClient

from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.redis import get_authorized_tokens_redis_key_current_month
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform

ANALYTICS_TOKEN = (
    "0a17753fecc38a5e259319e4524b55df439a98c1ff6326df7247263aa1192701cbe8799457cb1ac173590"
    "eecb11bfe62a34cc0798f95d8842124814c24f53ff"
)

OPERATIONAL_INFO = {
    "province": "CH",
    "exposure_permission": 0,
    "bluetooth_active": 1,
    "notification_permission": 1,
    "exposure_notification": 1,
    "last_risky_exposure_on": "2020-06-15",
}


@fixture
def operational_info() -> Dict[str, Any]:
    return deepcopy(OPERATIONAL_INFO)


@fixture
def headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {ANALYTICS_TOKEN}",
        "Immuni-Dummy-Data": "0",
        "Content-Type": "application/json; charset=utf-8",
    }


async def test_apple_operational_info_with_exposure(
    client: TestClient, operational_info: Dict[str, Any], headers: Dict[str, str]
) -> None:
    # authorize the current token for the upload
    await managers.analytics_redis.sadd(
        get_authorized_tokens_redis_key_current_month(with_exposure=True), ANALYTICS_TOKEN
    )

    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 1
    assert (
        OperationalInfo.objects.exclude("id").first().to_dict()
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
        get_authorized_tokens_redis_key_current_month(with_exposure=True), ANALYTICS_TOKEN
    )

    # only one call is authorized with a given token
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )
    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 1


async def test_apple_operational_info_without_exposure(
    client: TestClient, operational_info: Dict[str, Any], headers: Dict[str, str]
) -> None:
    assert OperationalInfo.objects.count() == 0
    operational_info["exposure_notification"] = 0

    # authorize the current token for the upload
    await managers.analytics_redis.sadd(
        get_authorized_tokens_redis_key_current_month(with_exposure=False), ANALYTICS_TOKEN
    )

    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 1
    assert (
        OperationalInfo.objects.first().to_dict()
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
        get_authorized_tokens_redis_key_current_month(with_exposure=False), ANALYTICS_TOKEN
    )

    # only one call is authorized with a given token
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )
    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 1


async def test_apple_operational_info_dummy(
    client: TestClient, operational_info: Dict[str, Any], headers: Dict[str, str]
) -> None:
    headers["Immuni-Dummy-Data"] = "1"
    response = await client.post(
        "/v1/analytics/apple/operational-info", json=operational_info, headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 0


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
