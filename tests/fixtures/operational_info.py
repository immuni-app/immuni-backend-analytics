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

from copy import deepcopy
from typing import Any, Dict

from pytest import fixture

OPERATIONAL_INFO = {
    "province": "CH",
    "exposure_permission": 0,
    "bluetooth_active": 1,
    "notification_permission": 1,
    "exposure_notification": 1,
    "last_risky_exposure_on": "2020-12-15",
}


@fixture
def operational_info() -> Dict[str, Any]:
    return deepcopy(OPERATIONAL_INFO)


ANALYTICS_TOKEN = (
    "746e35ce91c6e26db93981d57b38fd13b4d2c58c04d2775ceca3a0b43e12965ba532956cb3e72375782d3"
    "f93be3e8c09b3727d79287a92945633148e867eb762"
)
