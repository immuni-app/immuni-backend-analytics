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

from typing import Union
from unittest.mock import AsyncMock, MagicMock, call, patch

from freezegun import freeze_time
from pytest import mark

from immuni_analytics.celery.authorization.tasks.authorize_analytics_token import (
    _authorize_analytics_token,
)
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.request import BadFormatRequestError
from immuni_analytics.models.device_check import DeviceCheckData
from immuni_common.models.enums import Environment

TEST_ANALYTICS_TOKEN = "TEST_ANALYTICS_TOKEN"
TEST_DEVICE_TOKEN = "TEST_DEVICE_TOKEN"


@freeze_time("2020-01-31")
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token." "config.ENV",
    Environment.RELEASE,
)
@patch("asyncio.sleep", AsyncMock())
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
    "set_device_check_bits",
    return_value=AsyncMock(),
)
@mark.parametrize(
    "first_read_data,second_read_data,third_read_data",
    [
        (
            DeviceCheckData(False, False, None),
            DeviceCheckData(False, False, None),
            DeviceCheckData(True, False, "2020-01"),
        ),
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(True, False, "2020-01"),
        ),
    ],
)
async def test_authorize_analytics_token(
    mock_set_device_check_bits: AsyncMock,
    first_read_data: DeviceCheckData,
    second_read_data: DeviceCheckData,
    third_read_data: DeviceCheckData,
) -> None:
    with patch(
        "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
        "fetch_device_check_bits",
        AsyncMock(side_effect=[first_read_data, second_read_data, third_read_data]),
    ):
        await _authorize_analytics_token(TEST_ANALYTICS_TOKEN, TEST_DEVICE_TOKEN)

    members = await managers.analytics_redis.smembers(TEST_ANALYTICS_TOKEN)
    assert all(
        m in members for m in ["2020-01-01:0", "2020-01-01:1", "2020-02-01:0", "2020-02-01:1"]
    )
    assert mock_set_device_check_bits.call_count == 2
    mock_set_device_check_bits.assert_has_calls(
        (
            call(TEST_DEVICE_TOKEN, bit0=True, bit1=False),
            call(TEST_DEVICE_TOKEN, bit0=False, bit1=False),
        ),
        any_order=False,
    )


@freeze_time("2020-01-31")
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token." "config.ENV",
    Environment.RELEASE,
)
@patch("asyncio.sleep", AsyncMock())
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
    "set_device_check_bits",
    AsyncMock(),
)
@patch("immuni_analytics.celery.authorization.tasks.authorize_analytics_token._LOGGER.warning")
@mark.parametrize(
    "first_read_data,second_read_data,third_read_data",
    [
        (
            DeviceCheckData(False, False, "2020-01"),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, "2020-02"),  # should never happen
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
    ],
)
async def test_authorize_analytics_token_used_in_current_month(
    warning_logger: MagicMock,
    first_read_data: DeviceCheckData,
    second_read_data: RuntimeError,
    third_read_data: RuntimeError,
) -> None:
    with patch(
        "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
        "fetch_device_check_bits",
        AsyncMock(side_effect=[first_read_data, second_read_data, third_read_data]),
    ):
        await _authorize_analytics_token(TEST_ANALYTICS_TOKEN, TEST_DEVICE_TOKEN)

    warning_logger.assert_called_once_with(
        "Found token already used in current month.",
        extra=dict(
            env=config.ENV.value,
            bit0=first_read_data.bit0,
            bit1=first_read_data.bit1,
            last_update_time=first_read_data.last_update_time,
        ),
    )
    assert not await managers.analytics_redis.smembers(TEST_ANALYTICS_TOKEN)


@freeze_time("2020-01-31")
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token." "config.ENV",
    Environment.RELEASE,
)
@patch("asyncio.sleep", AsyncMock())
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
    "set_device_check_bits",
    return_value=AsyncMock(),
)
@patch("immuni_analytics.celery.authorization.tasks.authorize_analytics_token._LOGGER.warning")
@mark.parametrize(
    "first_read_data,second_read_data,third_read_data",
    [
        (
            DeviceCheckData(True, False, "2019-01"),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(True, True, "2019-01"),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, True, "2019-01"),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
    ],
)
async def test_authorize_analytics_token_first_step_not_compliant(
    warning_logger: MagicMock,
    mock_set_device_check_bits: AsyncMock,
    first_read_data: DeviceCheckData,
    second_read_data: RuntimeError,
    third_read_data: RuntimeError,
) -> None:
    with patch(
        "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
        "fetch_device_check_bits",
        AsyncMock(side_effect=[first_read_data, second_read_data, third_read_data]),
    ):
        await _authorize_analytics_token(TEST_ANALYTICS_TOKEN, TEST_DEVICE_TOKEN)

    warning_logger.assert_called_once_with(
        "Found token not default configuration compliant in first step.",
        extra=dict(
            env=config.ENV.value,
            bit0=first_read_data.bit0,
            bit1=first_read_data.bit1,
            last_update_time=first_read_data.last_update_time,
        ),
    )
    mock_set_device_check_bits.assert_called_once_with(TEST_DEVICE_TOKEN, bit0=True, bit1=True)
    assert not await managers.analytics_redis.smembers(TEST_ANALYTICS_TOKEN)


@freeze_time("2020-01-31")
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token." "config.ENV",
    Environment.RELEASE,
)
@patch("asyncio.sleep", AsyncMock())
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
    "set_device_check_bits",
    return_value=AsyncMock(),
)
@patch("immuni_analytics.celery.authorization.tasks.authorize_analytics_token._LOGGER.warning")
@mark.parametrize(
    "first_read_data,second_read_data,third_read_data",
    [
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(True, False, "2020-01"),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, True, "2020-01"),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(True, True, "2020-01"),
            RuntimeError("Should not call this function."),
        ),
    ],
)
async def test_authorize_analytics_token_second_step_not_compliant(
    warning_logger: MagicMock,
    mock_set_device_check_bits: AsyncMock,
    first_read_data: DeviceCheckData,
    second_read_data: DeviceCheckData,
    third_read_data: RuntimeError,
) -> None:
    with patch(
        "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
        "fetch_device_check_bits",
        AsyncMock(side_effect=[first_read_data, second_read_data, third_read_data]),
    ):
        await _authorize_analytics_token(TEST_ANALYTICS_TOKEN, TEST_DEVICE_TOKEN)

    warning_logger.assert_called_once_with(
        "Found token not default configuration compliant in second step.",
        extra=dict(
            env=config.ENV.value,
            bit0=second_read_data.bit0,
            bit1=second_read_data.bit1,
            last_update_time=second_read_data.last_update_time,
        ),
    )
    mock_set_device_check_bits.assert_called_once_with(TEST_DEVICE_TOKEN, bit0=True, bit1=True)
    assert not await managers.analytics_redis.smembers(TEST_ANALYTICS_TOKEN)


@freeze_time("2020-01-31")
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token." "config.ENV",
    Environment.RELEASE,
)
@patch("asyncio.sleep", AsyncMock())
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
    "set_device_check_bits",
    return_value=AsyncMock(),
)
@patch("immuni_analytics.celery.authorization.tasks.authorize_analytics_token._LOGGER.warning")
@mark.parametrize(
    "first_read_data,second_read_data,third_read_data",
    [
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, False, "2019-01"),
        ),
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, True, "2020-01"),
        ),
        (
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(False, False, "2019-01"),
            DeviceCheckData(True, True, "2020-01"),
        ),
    ],
)
async def test_authorize_analytics_token_third_step_not_compliant(
    warning_logger: MagicMock,
    mock_set_device_check_bits: AsyncMock,
    first_read_data: DeviceCheckData,
    second_read_data: DeviceCheckData,
    third_read_data: DeviceCheckData,
) -> None:
    with patch(
        "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
        "fetch_device_check_bits",
        AsyncMock(side_effect=[first_read_data, second_read_data, third_read_data]),
    ):
        await _authorize_analytics_token(TEST_ANALYTICS_TOKEN, TEST_DEVICE_TOKEN)

    warning_logger.assert_called_once_with(
        "Found token not authorization configuration compliant in third step.",
        extra=dict(
            env=config.ENV.value,
            bit0=third_read_data.bit0,
            bit1=third_read_data.bit1,
            last_update_time=third_read_data.last_update_time,
        ),
    )
    assert mock_set_device_check_bits.call_count == 2
    mock_set_device_check_bits.assert_has_calls(
        (
            call(TEST_DEVICE_TOKEN, bit0=True, bit1=False),
            call(TEST_DEVICE_TOKEN, bit0=True, bit1=True),
        ),
        any_order=False,
    )
    assert not await managers.analytics_redis.smembers(TEST_ANALYTICS_TOKEN)


@freeze_time("2020-01-31")
@patch(
    "immuni_analytics.celery.authorization.tasks.authorize_analytics_token." "config.ENV",
    Environment.RELEASE,
)
@patch("asyncio.sleep", AsyncMock())
@mark.parametrize(
    "first_read_data,second_read_data,third_read_data,first_set_data,second_set_data",
    [
        (
            BadFormatRequestError(),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, None),
            BadFormatRequestError(),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, None),
            DeviceCheckData(False, False, None),
            RuntimeError("Should not call this function."),
            BadFormatRequestError(),
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, None),
            DeviceCheckData(False, False, None),
            BadFormatRequestError(),
            None,
            RuntimeError("Should not call this function."),
        ),
        (
            DeviceCheckData(False, False, None),
            DeviceCheckData(False, False, None),
            DeviceCheckData(True, False, "2020-01"),
            None,
            BadFormatRequestError(),
        ),
    ],
)
async def test_authorize_analytics_token_bad_format(
    first_read_data: Union[DeviceCheckData, BadFormatRequestError, RuntimeError],
    second_read_data: Union[DeviceCheckData, BadFormatRequestError, RuntimeError],
    third_read_data: Union[DeviceCheckData, BadFormatRequestError, RuntimeError],
    first_set_data: Union[None, BadFormatRequestError, RuntimeError],
    second_set_data: Union[None, BadFormatRequestError, RuntimeError],
) -> None:
    with patch(
        "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
        "fetch_device_check_bits",
        AsyncMock(side_effect=[first_read_data, second_read_data, third_read_data]),
    ):
        with patch(
            "immuni_analytics.celery.authorization.tasks.authorize_analytics_token."
            "set_device_check_bits",
            AsyncMock(side_effect=[first_set_data, second_set_data]),
        ):
            await _authorize_analytics_token(TEST_ANALYTICS_TOKEN, TEST_DEVICE_TOKEN)

    assert not await managers.analytics_redis.smembers(TEST_ANALYTICS_TOKEN)
