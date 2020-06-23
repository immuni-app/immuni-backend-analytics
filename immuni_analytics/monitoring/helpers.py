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

from functools import wraps
from http.client import HTTPResponse
from typing import Any, Callable, Coroutine

from immuni_analytics.monitoring.api import OPERATIONAL_INFO_REQUESTS
from immuni_common.core.exceptions import ApiException
from immuni_common.helpers.sanic import validate
from immuni_common.models.enums import Location, Platform
from immuni_common.models.marshmallow.fields import IntegerBoolField
from immuni_common.models.swagger import HeaderImmuniDummyData

_ENDPOINT_PLATFORM_TO_PLATFORM = {"apple": Platform.IOS, "google": Platform.ANDROID}


def monitor_operational_info(f: Callable[..., Coroutine[Any, Any, HTTPResponse]]) -> Callable:
    """
    Decorator to monitor operational info requests metrics.

    :param f: the endpoint function to decorate.
    :return: the decorated function.
    """

    @wraps(f)
    @validate(
        location=Location.HEADERS,
        is_dummy=IntegerBoolField(
            required=True, allow_strings=True, data_key=HeaderImmuniDummyData.DATA_KEY,
        ),
    )
    async def _wrapper(*args: Any, is_dummy: bool, **kwargs: Any) -> HTTPResponse:
        request = args[0]
        platform = _ENDPOINT_PLATFORM_TO_PLATFORM[request.uri_template.split("/")[3]]
        province = kwargs["province"]
        try:
            response = await f(*args, **kwargs)
            OPERATIONAL_INFO_REQUESTS.labels(
                is_dummy, platform.value, province, response.status
            ).inc()
        except ApiException as error:
            OPERATIONAL_INFO_REQUESTS.labels(
                is_dummy, platform.value, province, error.status_code.value
            ).inc()
            raise
        return response

    return _wrapper
