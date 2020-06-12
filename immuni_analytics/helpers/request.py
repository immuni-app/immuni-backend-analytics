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

import logging
from typing import Any, Callable, Dict

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ServerUnavailableError(Exception):
    """Raised when the server returns a 5xx error code"""


class BadFormatRequestError(Exception):
    """Raised when the server returns a 4xx error code"""


def after_log() -> Callable[[RetryCallState], None]:
    """After call strategy that logs the finished attempt"""

    def log_it(retry_state: RetryCallState) -> None:
        """Logs the error and the attempt"""
        exc = retry_state.outcome.exception()
        url = retry_state.kwargs.get("url")
        logger.warning(
            "HTTP request to url %s failed (attempt %d)",
            url,
            retry_state.attempt_number,
            extra=dict(request_args=retry_state, request_kwargs=retry_state.kwargs),
        )

    return log_it


@retry(
    retry=retry_if_exception_type((ClientError, TimeoutError, ServerUnavailableError)),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    after=after_log(),
)
async def post_with_retry(
    session: ClientSession, *, url: str, json: Dict[str, Any], headers: Dict[str, str]
) -> bytes:
    """
    Wrapper around aiohttp post with retry strategy.

    :raises: BadFormatRequestError, ServerUnavailableError, ClientError, TimeoutError
    :return: the client response if successful
    """
    # TODO timeout from config
    async with session.post(
        url=url, json=json, headers=headers, timeout=ClientTimeout(total=10)
    ) as response:
        if response.status >= 500:
            raise ServerUnavailableError()
        if response.status >= 400:
            raise BadFormatRequestError()

        return await response.read()
