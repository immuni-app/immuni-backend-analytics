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

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from pytest import mark
from pytest_sanic.utils import TestClient
from sanic import Sanic
from sanic.request import Request
from sanic.response import HTTPResponse

from immuni_analytics.monitoring.helpers import (
    _ENDPOINT_PLATFORM_TO_PLATFORM,
    monitor_operational_info,
)
from immuni_common.core.exceptions import ApiException


@mark.parametrize(
    "endpoint_platform, should_raise",
    tuple(
        (platform, should_raise)
        for platform in ("apple", "google")
        for should_raise in (True, False)
    ),
)
@patch("immuni_analytics.monitoring.helpers.OPERATIONAL_INFO_REQUESTS.labels")
async def test_monitor_operational_info(
    metrics_increment_method: MagicMock,
    sanic: Sanic,
    client: TestClient,
    endpoint_platform: str,
    should_raise: bool,
) -> None:
    route = f"/first/second/{endpoint_platform}/{str(should_raise).lower()}"

    @sanic.route(route)
    @monitor_operational_info
    async def dummy(request: Request) -> HTTPResponse:
        if should_raise:
            raise ApiException()
        return HTTPResponse(status=HTTPStatus.OK)

    await client.get(route, headers={"Immuni-Dummy-Data": "1"})
    metrics_increment_method.assert_called_once_with(
        True,
        _ENDPOINT_PLATFORM_TO_PLATFORM[endpoint_platform],
        ApiException.status_code.value if should_raise else HTTPStatus.OK.value,
    )
