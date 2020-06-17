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
import json
from datetime import date, datetime
from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from freezegun import freeze_time
from pytest import fixture, mark
from pytest_sanic.utils import TestClient

from immuni_analytics.celery.authorization.tasks.verify_safety_net_attestation import (
    _verify_safety_net_attestation,
)
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.safety_net import get_redis_key
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform
from tests.fixtures.safety_net import POST_BODY_WITH_EXPOSURE, POST_TIMESTAMP, TEST_APK_DIGEST
from tests.helpers.test_safety_net import _operational_info_from_post_body


@fixture
def headers() -> Dict[str, str]:
    return {"Immuni-Dummy-Data": "0", "Content-Type": "application/json; charset=utf-8"}


@freeze_time(datetime.utcfromtimestamp(POST_TIMESTAMP))
async def test_google_operational_info_with_exposure(
    client: TestClient, safety_net_post_body_with_exposure: Dict[str, Any], headers: Dict[str, str]
) -> None:
    with patch("immuni_analytics.helpers.safety_net.config.SAFETY_NET_APK_DIGEST", TEST_APK_DIGEST):
        with patch("immuni_analytics.apis.analytics.verify_safety_net_attestation.delay"):
            response = await client.post(
                "/v1/analytics/google/operational-info",
                json=safety_net_post_body_with_exposure,
                headers=headers,
            )
            # FIXME: cannot mock an awaitable, cannot run the real delay as it tries to create
            #  a new event loop
            await _verify_safety_net_attestation(
                safety_net_post_body_with_exposure["signed_attestation"],
                safety_net_post_body_with_exposure["salt"],
                _operational_info_from_post_body(safety_net_post_body_with_exposure),
                safety_net_post_body_with_exposure["last_risky_exposure_on"],
            )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 1
    assert (
        json.loads(await managers.analytics_redis.lpop(config.OPERATIONAL_INFO_QUEUE_KEY))
        == OperationalInfo(
            platform=Platform.ANDROID,
            province=safety_net_post_body_with_exposure["province"],
            exposure_permission=safety_net_post_body_with_exposure["exposure_permission"],
            bluetooth_active=safety_net_post_body_with_exposure["bluetooth_active"],
            notification_permission=safety_net_post_body_with_exposure["notification_permission"],
            exposure_notification=safety_net_post_body_with_exposure["exposure_notification"],
            last_risky_exposure_on=date.fromisoformat(
                safety_net_post_body_with_exposure["last_risky_exposure_on"]
            ),
        ).to_dict()
    )
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        == "1"
    )


@freeze_time(datetime.utcfromtimestamp(POST_TIMESTAMP))
async def test_google_operational_info_without_exposure(
    client: TestClient,
    safety_net_post_body_without_exposure: Dict[str, Any],
    headers: Dict[str, str],
) -> None:
    with patch("immuni_analytics.helpers.safety_net.config.SAFETY_NET_APK_DIGEST", TEST_APK_DIGEST):
        with patch("immuni_analytics.apis.analytics.verify_safety_net_attestation.delay"):
            response = await client.post(
                "/v1/analytics/google/operational-info",
                json=safety_net_post_body_without_exposure,
                headers=headers,
            )
            # FIXME: cannot mock an awaitable, cannot run the real delay as it tries to create
            #  a new event loop
            await _verify_safety_net_attestation(
                safety_net_post_body_without_exposure["signed_attestation"],
                safety_net_post_body_without_exposure["salt"],
                _operational_info_from_post_body(safety_net_post_body_without_exposure),
                safety_net_post_body_without_exposure["last_risky_exposure_on"],
            )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 1
    assert (
        json.loads(await managers.analytics_redis.lpop(config.OPERATIONAL_INFO_QUEUE_KEY))
        == OperationalInfo(
            platform=Platform.ANDROID,
            province=safety_net_post_body_without_exposure["province"],
            exposure_permission=safety_net_post_body_without_exposure["exposure_permission"],
            bluetooth_active=safety_net_post_body_without_exposure["bluetooth_active"],
            notification_permission=safety_net_post_body_without_exposure[
                "notification_permission"
            ],
            exposure_notification=safety_net_post_body_without_exposure["exposure_notification"],
            last_risky_exposure_on=None,
        ).to_dict()
    )
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_without_exposure["salt"])
        )
        == "1"
    )


@freeze_time(datetime.utcfromtimestamp(POST_TIMESTAMP))
async def test_google_operational_info_dummy(
    client: TestClient, safety_net_post_body_with_exposure: Dict[str, Any], headers: Dict[str, str]
) -> None:
    headers["Immuni-Dummy-Data"] = "1"

    response = await client.post(
        "/v1/analytics/google/operational-info",
        json=safety_net_post_body_with_exposure,
        headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert OperationalInfo.objects.count() == 0
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        is None
    )


@freeze_time(datetime.utcfromtimestamp(POST_TIMESTAMP))
@patch("immuni_analytics.apis.analytics._LOGGER.warning")
async def test_google_operational_info_used_salt(
    warning_logger: MagicMock,
    client: TestClient,
    safety_net_post_body_with_exposure: Dict[str, Any],
    headers: Dict[str, str],
) -> None:
    with patch("immuni_analytics.helpers.safety_net.config.SAFETY_NET_APK_DIGEST", TEST_APK_DIGEST):
        with patch("immuni_analytics.apis.analytics.verify_safety_net_attestation.delay"):
            response = await client.post(
                "/v1/analytics/google/operational-info",
                json=safety_net_post_body_with_exposure,
                headers=headers,
            )
            # FIXME: cannot mock an awaitable, cannot run the real delay as it tries to create
            #  a new event loop
            await _verify_safety_net_attestation(
                safety_net_post_body_with_exposure["signed_attestation"],
                safety_net_post_body_with_exposure["salt"],
                _operational_info_from_post_body(safety_net_post_body_with_exposure),
                safety_net_post_body_with_exposure["last_risky_exposure_on"],
            )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 1
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        == "1"
    )

    response = await client.post(
        "/v1/analytics/google/operational-info",
        json=safety_net_post_body_with_exposure,
        headers=headers,
    )

    assert response.status == HTTPStatus.NO_CONTENT.value
    assert await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY) == 1
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        == "1"
    )
    warning_logger.assert_called_once_with(
        "Found previously used salt.",
        extra=dict(
            signed_attestation=safety_net_post_body_with_exposure["signed_attestation"],
            salt=safety_net_post_body_with_exposure["salt"],
        ),
    )


@mark.parametrize(
    "bad_data",
    [
        {k: v for k, v in POST_BODY_WITH_EXPOSURE.items() if k != excluded}
        for excluded in POST_BODY_WITH_EXPOSURE
    ],
)
async def test_google_operational_info_bad_request(
    client: TestClient, bad_data: Dict[str, Any], headers: Dict[str, str]
) -> None:
    response = await client.post(
        "/v1/analytics/google/operational-info", json=bad_data, headers=headers
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."

    assert OperationalInfo.objects.count() == 0


@mark.parametrize("dummy_header", ["random", "-1", ""])
async def test_upload_bad_request_dummy_header(
    client: TestClient,
    safety_net_post_body_with_exposure: Dict[str, Any],
    headers: Dict[str, str],
    dummy_header: str,
) -> None:
    headers["Immuni-Dummy-Data"] = dummy_header

    response = await client.post(
        "/v1/analytics/google/operational-info",
        json=safety_net_post_body_with_exposure,
        headers=headers,
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."
    assert OperationalInfo.objects.count() == 0
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        is None
    )


@mark.parametrize("province", ["asd", "ZZZ", "", None])
async def test_invalid_province(
    client: TestClient,
    safety_net_post_body_with_exposure: Dict[str, Any],
    headers: Dict[str, str],
    province: str,
) -> None:
    safety_net_post_body_with_exposure["province"] = province

    response = await client.post(
        "/v1/analytics/google/operational-info",
        json=safety_net_post_body_with_exposure,
        headers=headers,
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."
    assert OperationalInfo.objects.count() == 0
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        is None
    )


@mark.parametrize("last_risky_exposure_on", ["1970-01-01", "ZZZ", "", None])
async def test_invalid_last_risky_exposure(
    client: TestClient,
    safety_net_post_body_with_exposure: Dict[str, Any],
    headers: Dict[str, str],
    last_risky_exposure_on: str,
) -> None:
    safety_net_post_body_with_exposure["last_risky_exposure_on"] = last_risky_exposure_on

    response = await client.post(
        "/v1/analytics/google/operational-info",
        json=safety_net_post_body_with_exposure,
        headers=headers,
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."
    assert OperationalInfo.objects.count() == 0
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        is None
    )


@mark.parametrize(
    "field, value",
    [  # type: ignore
        (field, value)
        for field in [
            "exposure_permission",
            "bluetooth_active",
            "notification_permission",
            "exposure_notification",
        ]
        for value in [-1, None, "", "string", {}]
    ],
)
async def test_invalid_integer_booleans(
    client: TestClient,
    safety_net_post_body_with_exposure: Dict[str, Any],
    headers: Dict[str, str],
    field: str,
    value: Any,
) -> None:
    safety_net_post_body_with_exposure[field] = value

    response = await client.post(
        "/v1/analytics/google/operational-info",
        json=safety_net_post_body_with_exposure,
        headers=headers,
    )

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."
    assert OperationalInfo.objects.count() == 0
    assert (
        await managers.analytics_redis.get(
            get_redis_key(safety_net_post_body_with_exposure["salt"])
        )
        is None
    )
