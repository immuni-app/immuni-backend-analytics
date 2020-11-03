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

from mongoengine import ValidationError
from sanic.response import HTTPResponse

from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.core.exceptions import SchemaValidationException
from immuni_common.models.enums import Platform


def inject_operational_info(
    platform: Platform,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, HTTPResponse]]],
    Callable[..., Coroutine[Any, Any, HTTPResponse]],
]:
    """
    Validates all of the operational info parameters and injects them as a single model to the
    decorated function.

    :param platform: the platform the operation info is associated with.
    :return: the decorated function.
    """

    def _wrapper(
        f: Callable[..., Coroutine[Any, Any, HTTPResponse]]
    ) -> Callable[..., Coroutine[Any, Any, HTTPResponse]]:
        async def _wrapped_function(*args: Any, **kwargs: Any) -> HTTPResponse:
            """
            Validate and prepare the OperationalInfo document to be used by the decorated function.

            :param args: the positional arguments.
            :param kwargs: the keyword arguments.
            :return: the function HTTPResponse return value.
            """
            kwargs["operational_info"] = OperationalInfo(
                platform=platform,
                build=kwargs.get("build"),
                province=kwargs.get("province"),
                exposure_permission=kwargs.get("exposure_permission"),
                bluetooth_active=kwargs.get("bluetooth_active"),
                notification_permission=kwargs.get("notification_permission"),
                exposure_notification=kwargs.get("exposure_notification"),
                last_risky_exposure_on=kwargs.get("last_risky_exposure_on")
                if kwargs.get("exposure_notification")
                else None,
            )

            try:
                kwargs["operational_info"].validate()
            except ValidationError as error:
                raise SchemaValidationException(str(error)) from error

            return await f(*args, **kwargs)

        return _wrapped_function

    return _wrapper
