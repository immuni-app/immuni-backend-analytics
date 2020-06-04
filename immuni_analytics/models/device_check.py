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

from dataclasses import dataclass
from datetime import date
from typing import Optional


def current_month() -> date:
    """
    Returns a datetime object representing the first day of the current month
    """
    return date.today().replace(day=1)


@dataclass(frozen=True)
class DeviceCheckData:
    """
    A representation of the response returned from the DeviceCheck API.
    """

    bit0: bool
    bit1: bool
    last_update_time: Optional[str]  # YYYY-MM formatted
