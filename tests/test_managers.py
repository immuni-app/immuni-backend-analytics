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

from unittest.mock import PropertyMock, patch

from pytest import raises

from immuni_analytics.core.managers import Managers, managers


def test_mongo_failure() -> None:
    with patch.object(Managers, "_analytics_mongo", new_callable=PropertyMock) as mock:
        mock.return_value = None
        with raises(RuntimeError):
            managers.analytics_mongo


def test_analytics_redis_failure() -> None:
    with patch.object(Managers, "_analytics_redis", new_callable=PropertyMock) as mock:
        mock.return_value = None
        with raises(RuntimeError):
            managers.analytics_redis


async def test_teardown_on_uninitialized() -> None:
    uninitialized_managers = Managers()
    await uninitialized_managers.teardown()
