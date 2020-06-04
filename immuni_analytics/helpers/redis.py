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

from immuni_analytics.helpers.date_utils import current_month, next_month


def get_authorized_tokens_redis_key_current_month(with_exposure: bool) -> str:
    """
    Returns the redis key associated with the authorized analytics tokens for the current month.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
    with exposure or not
    :return: the redis key
    """
    return (
        f"authorized_{'with_exposure' if with_exposure else 'without_exposure'}:"
        f"{current_month().isoformat()}"
    )


def get_authorized_tokens_redis_key_next_month(with_exposure: bool) -> str:
    """
    Returns the redis key associated with the authorized analytics tokens for the next month.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
    with exposure or not
    :return: the redis key
    """
    return (
        f"authorized_{'with_exposure' if with_exposure else 'without_exposure'}:"
        f"{next_month().isoformat()}"
    )
