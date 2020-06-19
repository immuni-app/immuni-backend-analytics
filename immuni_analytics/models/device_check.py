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
    def _last_update_month(self) -> date:
        """
        Generate the date object of the last update from the last_update_time.

        :return: a date object representing the last update.
        :raises: ValueError if the last_update_time is None.
        """
        if self.last_update_time is None:
            raise ValueError("DeviceCheckData last_update_time is None.")

        return date.fromisoformat(f"{self.last_update_time}-01")

    @property
    def used_in_current_month(self) -> bool:
        """
        Whether the device has been already used to validate a token in the current month
        """
        return self.last_update_time is not None and current_month() <= self._last_update_month

    @property
    def is_default_configuration(self) -> bool:
        """
        Check if the bits are set as expected in the first or second read operations.
        Namely, if both bits are False.

        :return: True if the configuration is correct, False otherwise.
        """
        return not self.bit0 and not self.bit1

    @property
    def is_authorized(self) -> bool:
        """
        Check if the bits are set as expected for the third read.
        Namely, if bit0 = True and bit1 = False

        :return: True if the configuration is correct, False otherwise.
        """
        return self.bit0 and not self.bit1

    @property
    def is_blacklisted(self) -> bool:
        """
        Check if the bits are as expected for a blacklisted device.
        Namely, if both bits are True.

        :return: True if the if the device is blacklisted, False otherwise.
        """
        return self.bit0 and self.bit1
