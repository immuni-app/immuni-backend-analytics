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

from datetime import date
from typing import Optional

from freezegun import freeze_time
from pytest import mark, raises

from immuni_analytics.models.device_check import DeviceCheckData


@mark.parametrize(
    "bit0,bit1,last_update_time,expected",
    [
        (False, False, "2020-08", date(2020, 8, 1)),
        (False, False, "2020-04", date(2020, 4, 1)),
        (True, False, "2020-08", date(2020, 8, 1)),
    ],
)
def test_device_check_data_last_month(
    bit0: bool, bit1: bool, last_update_time: Optional[str], expected: date
) -> None:
    data = DeviceCheckData(bit0, bit1, last_update_time)

    assert data._last_update_month == expected


def test_device_check_data_last_month_raises_if_none() -> None:
    data = DeviceCheckData(False, False, None)

    with raises(ValueError):
        data._last_update_month


@freeze_time("2020-06-10")
@mark.parametrize(
    "bit0,bit1,last_update_time,expected",
    [
        (False, False, "2020-06", True),
        (False, False, "2020-04", False),
        (False, False, "2020-05", False),
        (False, False, None, False),
        (True, False, "2020-04", False),
        (False, True, "2020-04", False),
        (True, True, "2020-04", False),
        (True, False, "2020-06", True),
        (False, True, "2020-06", True),
        (True, True, "2020-06", True),
        (False, False, "2020-07", True),
    ],
)
def test_device_check_data_used_in_current_month(
    bit0: bool, bit1: bool, last_update_time: Optional[str], expected: bool
) -> None:
    data = DeviceCheckData(bit0, bit1, last_update_time)

    assert data.used_in_current_month is expected


@freeze_time("2020-06-10")
@mark.parametrize(
    "bit0,bit1,last_update_time,expected",
    [
        (False, False, "2020-04", True),
        (False, False, "2020-05", True),
        (False, False, None, True),
        (True, False, "2020-04", False),
        (False, True, "2020-04", False),
        (True, True, "2020-04", False),
    ],
)
def test_device_check_data_is_default_config_compliant(
    bit0: bool, bit1: bool, last_update_time: Optional[str], expected: bool
) -> None:
    data = DeviceCheckData(bit0, bit1, last_update_time)

    assert data.is_default_configuration is expected


@freeze_time("2020-06-10")
@mark.parametrize(
    "bit0,bit1,last_update_time,expected",
    [
        (False, False, "2020-08", False),
        (False, False, "2020-06", False),
        (False, False, "2020-04", False),
        (False, False, "2020-05", False),
        (False, False, None, False),
        (True, False, "2020-04", True),
        (False, True, "2020-04", False),
        (True, True, "2020-04", False),
    ],
)
def test_device_check_data_is_authorized_config_compliant(
    bit0: bool, bit1: bool, last_update_time: Optional[str], expected: bool
) -> None:
    data = DeviceCheckData(bit0, bit1, last_update_time)

    assert data.is_authorized is expected


@freeze_time("2020-06-10")
@mark.parametrize(
    "bit0,bit1,last_update_time,expected",
    [
        (False, False, "2020-08", False),
        (False, False, "2020-06", False),
        (False, False, "2020-04", False),
        (False, False, "2020-05", False),
        (False, False, None, False),
        (True, False, "2020-04", False),
        (False, True, "2020-04", False),
        (True, True, "2020-04", True),
    ],
)
def test_device_check_data_is_blacklisted(
    bit0: bool, bit1: bool, last_update_time: Optional[str], expected: bool
) -> None:
    data = DeviceCheckData(bit0, bit1, last_update_time)

    assert data.is_blacklisted is expected
