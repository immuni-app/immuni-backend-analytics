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
from freezegun import freeze_time

from immuni_analytics.helpers.redis import (
    get_all_authorizations_for_upload,
    get_upload_authorization_member_for_current_month,
    get_upload_authorization_member_for_next_month,
)


@freeze_time("2020-01-31")
def test_get_upload_authorization_member_for_current_month_with_exposure() -> None:
    assert get_upload_authorization_member_for_current_month(with_exposure=True) == "2020-01-01:1"


@freeze_time("2020-01-31")
def test_get_upload_authorization_member_for_current_month_without_exposure() -> None:
    assert get_upload_authorization_member_for_current_month(with_exposure=False) == "2020-01-01:0"


@freeze_time("2020-01-31")
def test_get_upload_authorization_member_for_next_month_with_exposure() -> None:
    assert get_upload_authorization_member_for_next_month(with_exposure=True) == "2020-02-01:1"


@freeze_time("2020-01-31")
def test_get_upload_authorization_member_for_next_month_without_exposure() -> None:
    assert get_upload_authorization_member_for_next_month(with_exposure=False) == "2020-02-01:0"


@freeze_time("2019-12-15")
def test_get_upload_authorization_member_for_next_month_year_change() -> None:
    assert get_upload_authorization_member_for_next_month(with_exposure=False) == "2020-01-01:0"


@freeze_time("2019-12-15")
def test_get_all_authorizations_for_upload() -> None:
    assert get_all_authorizations_for_upload() == [
        "2019-12-01:1",
        "2019-12-01:0",
        "2020-01-01:1",
        "2020-01-01:0",
    ]
