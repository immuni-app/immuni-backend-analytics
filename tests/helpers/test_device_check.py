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

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
from freezegun import freeze_time
from pytest import mark, raises

from immuni_analytics.helpers.device_check import (
    DeviceCheckApiError,
    _generate_common_payload,
    _generate_device_check_jwt,
    _generate_headers,
    fetch_device_check_bits,
    set_device_check_bits,
)
from immuni_analytics.helpers.request import BadFormatRequestError, ServerUnavailableError
from immuni_analytics.models.device_check import DeviceCheckData


@freeze_time("2020-01-31")
@patch("immuni_analytics.helpers.device_check.config.APPLE_KEY_ID", "TEST_KEY_ID")
@patch("immuni_analytics.helpers.device_check.config.APPLE_CERTIFICATE_KEY", "TEST_CERTIFICATE_KEY")
@patch("immuni_analytics.helpers.device_check.config.APPLE_TEAM_ID", "TEST_TEAM_ID")
@patch("immuni_analytics.helpers.device_check.jwt.encode")
def test_generate_device_check_jwt(jwt_encode: MagicMock) -> None:
    _generate_device_check_jwt()

    jwt_encode.assert_called_once_with(
        payload={"iss": "TEST_TEAM_ID", "iat": int(datetime.utcnow().timestamp())},
        key="TEST_CERTIFICATE_KEY",
        algorithm="ES256",
        headers={"kid": "TEST_KEY_ID"},
    )


def test_generate_headers() -> None:
    with patch(
        "immuni_analytics.helpers.device_check._generate_device_check_jwt",
        return_value="TEST_BEARER",
    ):
        assert _generate_headers() == {"Authorization": "Bearer TEST_BEARER"}


@freeze_time("2020-01-31")
def test_generate_common_payload() -> None:
    with patch("immuni_analytics.helpers.device_check.uuid.uuid4", return_value="TEST_UUID"):
        assert _generate_common_payload() == {
            "transaction_id": "TEST_UUID",
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
        }


@patch(
    "immuni_analytics.helpers.device_check._generate_headers",
    MagicMock(return_value={"header": "test"}),
)
@patch(
    "immuni_analytics.helpers.device_check._generate_common_payload",
    MagicMock(return_value={"payload": "test"}),
)
@patch(
    "immuni_analytics.helpers.device_check.ClientSession",
    return_value=AsyncMock(**{"__aenter__.return_value": "test_session"}),
)
@mark.parametrize(
    "post_return, expected_result",
    [
        (b"Failed to find bit state", DeviceCheckData(False, False, None)),
        (
            b'{"bit0":false,"bit1":false,"last_update_time":"2020-01"}',
            DeviceCheckData(False, False, "2020-01"),
        ),
        (
            b'{"bit0":true,"bit1":false,"last_update_time":"2022-11"}',
            DeviceCheckData(True, False, "2022-11"),
        ),
    ],
)
async def test_fetch_device_check_bits_success(
    mock_session: MagicMock, post_return: bytes, expected_result: DeviceCheckData
) -> None:
    with patch(
        "immuni_analytics.helpers.device_check.post_with_retry",
        AsyncMock(return_value=post_return),
    ) as post:
        device_check_data = await fetch_device_check_bits("test_token")

        post.assert_called_once_with(
            "test_session",
            url="https://api.development.devicecheck.apple.com/v1/query_two_bits",
            json={"payload": "test", "device_token": "test_token"},
            headers={"header": "test"},
        )

    assert device_check_data == expected_result


@patch(
    "immuni_analytics.helpers.device_check._generate_headers", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check._generate_common_payload", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check.post_with_retry",
    AsyncMock(side_effect=BadFormatRequestError),
)
@patch(
    "immuni_analytics.helpers.device_check.ClientSession", return_value=AsyncMock(),
)
@patch("immuni_analytics.helpers.device_check._LOGGER.warning",)
async def test_fetch_device_check_bits_bad_format(
    warning_logger: MagicMock, mock_session: MagicMock
) -> None:
    with raises(DeviceCheckApiError):
        await fetch_device_check_bits("test_token")

        assert warning_logger.called_once_with(
            "The DeviceCheck API is not available.", extra={"device_token": "test_token"}
        )


@patch(
    "immuni_analytics.helpers.device_check._generate_headers", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check._generate_common_payload", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check.post_with_retry", AsyncMock(side_effect=ClientError()),
)
@patch(
    "immuni_analytics.helpers.device_check.ClientSession", return_value=AsyncMock(),
)
@patch("immuni_analytics.helpers.device_check._LOGGER.warning",)
@mark.parametrize("raised_exception", [ClientError, TimeoutError, ServerUnavailableError])
async def test_fetch_device_check_bits_server_unavailable(
    warning_logger: MagicMock, mock_session: MagicMock, raised_exception: Exception
) -> None:
    with patch(
        "immuni_analytics.helpers.device_check.post_with_retry",
        AsyncMock(side_effect=raised_exception),
    ):
        with raises(DeviceCheckApiError):
            await fetch_device_check_bits("test_token")

            assert warning_logger.called_once_with(
                "The DeviceCheck API is not available.", extra={"device_token": "test_token"}
            )


@patch(
    "immuni_analytics.helpers.device_check._generate_headers",
    MagicMock(return_value={"header": "test"}),
)
@patch(
    "immuni_analytics.helpers.device_check._generate_common_payload",
    MagicMock(return_value={"payload": "test"}),
)
@patch(
    "immuni_analytics.helpers.device_check.ClientSession",
    return_value=AsyncMock(**{"__aenter__.return_value": "test_session"}),
)
@mark.parametrize("bit0, bit1", [(False, False), (True, False), (False, True), (True, True)])
async def test_set_device_check_bits_success(
    mock_session: MagicMock, bit0: bool, bit1: bool
) -> None:
    with patch("immuni_analytics.helpers.device_check.post_with_retry", AsyncMock()) as post:
        await set_device_check_bits("test_token", bit0=bit0, bit1=bit1)

        post.assert_called_once_with(
            "test_session",
            url="https://api.development.devicecheck.apple.com/v1/update_two_bits",
            json={"payload": "test", "device_token": "test_token", "bit0": bit0, "bit1": bit1},
            headers={"header": "test"},
        )


@patch(
    "immuni_analytics.helpers.device_check._generate_headers", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check._generate_common_payload", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check.post_with_retry",
    AsyncMock(side_effect=BadFormatRequestError),
)
@patch(
    "immuni_analytics.helpers.device_check.ClientSession", return_value=AsyncMock(),
)
@patch("immuni_analytics.helpers.device_check._LOGGER.warning",)
async def test_set_device_check_bits_bad_format(
    warning_logger: MagicMock, mock_session: MagicMock
) -> None:
    with raises(DeviceCheckApiError):
        await set_device_check_bits("test_token", bit0=False, bit1=False)

        assert warning_logger.called_once_with(
            "The DeviceCheck API is not available.", extra={"device_token": "test_token"}
        )


@patch(
    "immuni_analytics.helpers.device_check._generate_headers", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check._generate_common_payload", MagicMock(return_value={}),
)
@patch(
    "immuni_analytics.helpers.device_check.ClientSession", return_value=AsyncMock(),
)
@patch("immuni_analytics.helpers.device_check._LOGGER.warning",)
@mark.parametrize("raised_exception", [ClientError, TimeoutError, ServerUnavailableError])
async def test_set_device_check_bits_server_unavailable(
    warning_logger: MagicMock, mock_session: MagicMock, raised_exception: Exception
) -> None:
    with patch(
        "immuni_analytics.helpers.device_check.post_with_retry",
        AsyncMock(side_effect=raised_exception),
    ):
        with raises(DeviceCheckApiError):
            await set_device_check_bits("test_token", bit0=False, bit1=False)

            assert warning_logger.called_once_with(
                "The DeviceCheck API is not available.", extra={"device_token": "test_token"}
            )
