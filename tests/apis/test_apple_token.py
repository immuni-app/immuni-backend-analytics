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

import base64
from http import HTTPStatus
from typing import Any, Dict
from unittest.mock import patch

from pytest import mark
from pytest_sanic.utils import TestClient

from immuni_analytics.celery.authorization_ios.tasks.authorize_analytics_token import (
    _add_analytics_token_to_redis,
)
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.redis import (
    get_upload_authorization_member_for_current_month,
    get_upload_authorization_member_for_next_month,
)
from tests.fixtures.operational_info import ANALYTICS_TOKEN

TOKEN_BODY = {
    "analytics_token": ANALYTICS_TOKEN,
    "device_token": base64.b64encode("test".encode("utf-8")).decode("utf-8"),
}


async def test_apple_token(client: TestClient) -> None:
    with patch("immuni_analytics.apis.analytics.authorize_analytics_token.delay"):
        response = await client.post("/v1/analytics/apple/token", json=TOKEN_BODY,)

        await _add_analytics_token_to_redis(ANALYTICS_TOKEN)

    assert response.status == HTTPStatus.ACCEPTED.value
    assert await managers.authorization_ios_redis.sismember(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_current_month(with_exposure=True)
    )
    assert await managers.authorization_ios_redis.sismember(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_current_month(with_exposure=False)
    )
    assert await managers.authorization_ios_redis.sismember(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_next_month(with_exposure=True)
    )
    assert await managers.authorization_ios_redis.sismember(
        ANALYTICS_TOKEN, get_upload_authorization_member_for_next_month(with_exposure=False)
    )

    response = await client.post(
        "/v1/analytics/apple/token",
        json={
            "analytics_token": ANALYTICS_TOKEN,
            "device_token": base64.b64encode("test".encode("utf-8")).decode("utf-8"),
        },
    )

    assert response.status == HTTPStatus.CREATED.value


@mark.parametrize(
    "bad_data", [{k: v for k, v in TOKEN_BODY.items() if k != excluded} for excluded in TOKEN_BODY],
)
async def test_google_operational_info_bad_request(
    bad_data: Dict[str, Any], client: TestClient
) -> None:
    response = await client.post("/v1/analytics/apple/token", json=bad_data)

    assert response.status == 400
    data = await response.json()
    assert data["message"] == "Request not compliant with the defined schema."
