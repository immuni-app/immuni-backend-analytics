import asyncio
import random
from http import HTTPStatus
from typing import Any, Callable, Coroutine

from sanic.response import HTTPResponse
from sanic_openapi import doc

from immuni_analytics.core import config
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.helpers.sanic import json_response, validate
from immuni_common.models.enums import Location, Platform
from immuni_common.models.marshmallow.fields import IntegerBoolField
from immuni_common.models.swagger import HeaderImmuniDummyData


async def wait_configured_time() -> None:
    """
    Wait for the configured time.
    This is usually useful to make dummy requests last a similar amount of time when compared to the
    real ones, or slow down potential brute force attacks.
    """
    await asyncio.sleep(
        random.normalvariate(
            config.DUMMY_REQUEST_TIMEOUT_MILLIS, config.DUMMY_REQUEST_TIMEOUT_SIGMA
        )
        / 1000.0
    )


def allows_dummy_requests(
    f: Callable[..., Coroutine[Any, Any, HTTPResponse]]
) -> Callable[..., Coroutine[Any, Any, HTTPResponse]]:
    """
    Decorator that allows handling dummy requests.
    :return: The decorated function.
    """

    @validate(
        location=Location.HEADERS,
        is_dummy=IntegerBoolField(
            required=True, allow_strings=True, data_key=HeaderImmuniDummyData.DATA_KEY,
        ),
    )
    @doc.consumes(HeaderImmuniDummyData(), location="header", required=True)
    async def _wrapper(*args: Any, is_dummy: bool, **kwargs: Any) -> HTTPResponse:
        if is_dummy:
            await wait_configured_time()
            return json_response(body=None, status=HTTPStatus.NO_CONTENT)
        return await f(*args, **kwargs)

    return _wrapper


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
