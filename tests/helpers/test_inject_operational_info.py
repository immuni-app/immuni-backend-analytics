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

from typing import Any, Dict

from pytest import mark, raises
from sanic.response import HTTPResponse

from immuni_analytics.helpers.api import inject_operational_info
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.core.exceptions import SchemaValidationException
from immuni_common.models.enums import Platform


@mark.parametrize("platform", list(Platform))
async def test_mongo_validation_raises(
    platform: Platform, operational_info: Dict[str, Any],
) -> None:
    async def _test(operational_info: OperationalInfo) -> HTTPResponse:
        """Don't care about this implementation."""

    with raises(SchemaValidationException):
        await inject_operational_info(platform)(_test)(**operational_info, build=dict())
