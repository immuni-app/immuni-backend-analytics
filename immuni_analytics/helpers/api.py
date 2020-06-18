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
