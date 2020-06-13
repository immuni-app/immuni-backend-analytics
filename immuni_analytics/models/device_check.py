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

from immuni_analytics.helpers.date_utils import current_month


@dataclass(frozen=True)
class DeviceCheckData:
    """
    A representation of the response returned from the DeviceCheck API.
    """

    bit0: bool
    bit1: bool
    last_update_time: Optional[str]  # YYYY-MM formatted

    @property
    def last_update_month(self) -> date:
        """
        Generate the date object of the last update from the last_update_time

        :return: a date object representing the last update
        """
        if self.last_update_time is None:
            raise ValueError("DeviceCheckData last_update_time is None")

        return date.fromisoformat(f"{self.last_update_time}-01")

    @property
    def is_default_configuration_compliant(self) -> bool:
        """
        Checks if the data represent an expected configuration for the first and second read.
        The correct configurations are:
        - The last_update_time is not defined
        - The last_update_time is at least one month ago and both bits are false

        :return: true if the configuration is correct, false otherwise.
        """
        if self.last_update_time is None or (
            current_month() > self.last_update_month and self.bit0 is False and self.bit1 is False
        ):
            return True
        return False

    @property
    def is_authorized_configuration_compliant(self) -> bool:
        """
        Checks if the data represent an expected configuration for the third read.
        The correct configuration is bit0 = True and bit1 = False

        :return: true if the configuration is correct, false otherwise.
        """
        if self.bit0 is True and self.bit1 is False:
            return True

        return False
