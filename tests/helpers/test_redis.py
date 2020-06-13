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
    get_authorized_tokens_redis_key_current_month,
    get_authorized_tokens_redis_key_next_month,
)


@freeze_time("2020-01-31")
def test_get_authorized_tokens_with_exposure_redis_key_current_month() -> None:
    assert (
        get_authorized_tokens_redis_key_current_month(with_exposure=True)
        == "authorized-with-exposure:2020-01-01"
    )


@freeze_time("2020-01-31")
def test_get_authorized_tokens_without_exposure_redis_key_current_month() -> None:
    assert (
        get_authorized_tokens_redis_key_current_month(with_exposure=False)
        == "authorized-without-exposure:2020-01-01"
    )


@freeze_time("2020-01-31")
def test_get_authorized_tokens_with_exposure_redis_key_next_month() -> None:
    assert (
        get_authorized_tokens_redis_key_next_month(with_exposure=True)
        == "authorized-with-exposure:2020-02-01"
    )


@freeze_time("2020-01-31")
def test_get_authorized_tokens_without_exposure_redis_key_next_month() -> None:
    assert (
        get_authorized_tokens_redis_key_next_month(with_exposure=False)
        == "authorized-without-exposure:2020-02-01"
    )


@freeze_time("2019-12-15")
def test_get_authorized_tokens_without_exposure_redis_key_next_month_year_change() -> None:
    assert (
        get_authorized_tokens_redis_key_next_month(with_exposure=False)
        == "authorized-without-exposure:2020-01-01"
    )
