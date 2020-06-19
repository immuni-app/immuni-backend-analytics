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

from typing import Any, Callable, Coroutine

from sanic.response import HTTPResponse

from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform


def inject_operational_info(
    f: Callable[..., Coroutine[Any, Any, HTTPResponse]]
) -> Callable[..., Coroutine[Any, Any, HTTPResponse]]:
    """
    Validates all of the operational info parameters and injects them as
     a single model to the decorated function.
    :param f: The function to inject operational info to.
    :return: The decorated function.
    """

    async def _wrapper(*args: Any, **kwargs: Any) -> HTTPResponse:
        """
        Validates and prepares the OperationalInfo document to be used by the decorated function.
        """
        kwargs["operational_info"] = OperationalInfo(
            platform=Platform.IOS,
            province=kwargs.get("province"),
            exposure_permission=kwargs.get("exposure_permission"),
            bluetooth_active=kwargs.get("bluetooth_active"),
            notification_permission=kwargs.get("notification_permission"),
            exposure_notification=kwargs.get("exposure_notification"),
            last_risky_exposure_on=kwargs.get("last_risky_exposure_on")
            if kwargs.get("exposure_notification")
            else None,
        )
        return await f(*args, **kwargs)

    return _wrapper
