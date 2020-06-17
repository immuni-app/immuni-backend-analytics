import asyncio
import random
from http import HTTPStatus
from typing import Callable, Any, Coroutine

from immuni_common.helpers.sanic import validate, json_response
from immuni_common.models.enums import Location
from immuni_common.models.marshmallow.fields import IntegerBoolField
from immuni_common.models.swagger import HeaderImmuniDummyData
from sanic.response import HTTPResponse
from sanic_openapi import doc

from immuni_analytics.core import config


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
