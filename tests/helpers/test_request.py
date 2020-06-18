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

from typing import Any, Optional, Type

from aiohttp import ClientResponse, ClientSession
from aiohttp.client import _RequestContextManager
from aiohttp.typedefs import StrOrURL
from mypy.ipc import TracebackType
from pytest import raises
from tenacity import RetryError

from immuni_analytics.helpers.request import (
    BadFormatRequestError,
    ServerUnavailableError,
    post_with_retry,
)


class MockedClientResponse(ClientResponse):
    RESPONSE_BODY = b"the body."

    def __init__(self, status: int) -> None:
        self.status = status

    async def read(self) -> bytes:
        return self.RESPONSE_BODY

    def __repr__(self) -> str:
        return f"status: {self.status}"


class MockedRequestContextManager(_RequestContextManager):
    def __init__(self, post_response_status: int) -> None:
        self.post_response_status = post_response_status

    async def __aenter__(self) -> ClientResponse:
        return MockedClientResponse(self.post_response_status)

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        pass


class MockedClientSession(ClientSession):
    def __init__(self, post_response_status: int) -> None:
        self.post_response_status = post_response_status

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self._connector = None

    def post(self, url: StrOrURL, *, data: Any = None, **kwargs: Any) -> _RequestContextManager:
        return MockedRequestContextManager(self.post_response_status)


_PAYLOAD = {"a": "payload"}
_URL = "http://www.example.com"


async def test_post_with_retry_2xx() -> None:
    async with MockedClientSession(post_response_status=200) as session:
        response_body = await post_with_retry(session, url=_URL, json=_PAYLOAD, headers=dict())

    assert response_body == MockedClientResponse.RESPONSE_BODY


async def test_post_with_retry_4xx() -> None:
    async with MockedClientSession(post_response_status=400) as session:
        with raises(BadFormatRequestError):
            await post_with_retry(session, url=_URL, json=_PAYLOAD, headers=dict())


async def test_post_with_retry_5xx() -> None:
    async with MockedClientSession(post_response_status=500) as session:
        with raises(RetryError) as exception:
            await post_with_retry(session, url=_URL, json=_PAYLOAD, headers=dict())

        assert isinstance(exception.value.last_attempt._exception, ServerUnavailableError)
