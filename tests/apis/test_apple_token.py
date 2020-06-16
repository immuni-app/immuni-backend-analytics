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

import base64
from http import HTTPStatus
from unittest.mock import patch

from pytest_sanic.utils import TestClient

from immuni_analytics.celery.authorization.tasks.authorize_analytics_token import (
    _add_analytics_token_to_redis,
    _authorize_analytics_token,
)
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.redis import (
    get_authorized_tokens_redis_key_current_month,
    get_authorized_tokens_redis_key_next_month,
)

ANALYTICS_TOKEN = (
    "746e35ce91c6e26db93981d57b38fd13b4d2c58c04d2775ceca3a0b43e12965ba532956cb3e72375782d3"
    "f93be3e8c09b3727d79287a92945633148e867eb762"
)


async def test_apple_token(client: TestClient) -> None:
    with patch("immuni_analytics.apis.analytics.authorize_analytics_token.delay"):
        response = await client.post(
            "/v1/analytics/apple/token",
            json={
                "analytics_token": ANALYTICS_TOKEN,
                "device_token": base64.b64encode("test".encode("utf-8")).decode("utf-8"),
            },
        )

        await _add_analytics_token_to_redis(ANALYTICS_TOKEN)

    assert response.status == HTTPStatus.ACCEPTED.value
    assert await managers.analytics_redis.sismember(
        get_authorized_tokens_redis_key_current_month(with_exposure=True), ANALYTICS_TOKEN
    )
    assert await managers.analytics_redis.sismember(
        get_authorized_tokens_redis_key_current_month(with_exposure=False), ANALYTICS_TOKEN
    )
    assert await managers.analytics_redis.sismember(
        get_authorized_tokens_redis_key_next_month(with_exposure=True), ANALYTICS_TOKEN
    )
    assert await managers.analytics_redis.sismember(
        get_authorized_tokens_redis_key_next_month(with_exposure=False), ANALYTICS_TOKEN
    )

    response = await client.post(
        "/v1/analytics/apple/token",
        json={
            "analytics_token": ANALYTICS_TOKEN,
            "device_token": base64.b64encode("test".encode("utf-8")).decode("utf-8"),
        },
    )

    assert response.status == HTTPStatus.CREATED.value
