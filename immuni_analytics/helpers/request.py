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

import logging
from typing import Any, Dict

from aiohttp import ClientError, ClientSession, ClientTimeout
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from immuni_analytics.core import config
from immuni_common.core.exceptions import ImmuniException

_LOGGER = logging.getLogger(__name__)


class ServerUnavailableError(ImmuniException):
    """
    Raised when the server returns a 5xx error code.
    """


class BadFormatRequestError(ImmuniException):
    """
    Raised when the server returns a 4xx error code.
    """


def after_retry_callback(retry_state: RetryCallState) -> None:
    """
    Callback to execute after each retry attempt.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome is not None else None
    url = retry_state.kwargs.get("url")
    _LOGGER.warning(
        "Failed HTTP request.",
        extra=dict(exc=exc, request_args=retry_state, request_kwargs=retry_state.kwargs, url=url),
    )


@retry(
    retry=retry_if_exception_type(
        (ClientError, TimeoutError, ServerUnavailableError)
    ),  # type: ignore
    wait=wait_exponential(multiplier=1, min=2, max=10),  # type: ignore
    stop=stop_after_attempt(3),  # type: ignore
    after=after_retry_callback,
)
async def post_with_retry(
    session: ClientSession, *, url: str, json: Dict[str, Any], headers: Dict[str, str]
) -> bytes:
    """
    Wrapper around aiohttp post with retry strategy.

    :raises: BadFormatRequestError, ServerUnavailableError, ClientError, TimeoutError
    :return: the client response if successful.
    """
    params: Dict[str, Any] = dict(
        url=url,
        json=json,
        headers=headers,
        timeout=ClientTimeout(total=config.REQUESTS_TIMEOUT_SECONDS),
    )

    async with session.post(**params) as response:
        _LOGGER.info("Performed HTTP request.", extra=dict(request=params, response=response))
        if response.status >= 500:
            raise ServerUnavailableError()
        if response.status >= 400:
            raise BadFormatRequestError()

        return await response.read()
