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
import json

from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.date_utils import current_month, next_month
from immuni_analytics.models.operational_info import OperationalInfo


def get_authorized_tokens_redis_key_current_month(with_exposure: bool) -> str:
    """
    Generate the redis key associated with the authorized analytics tokens for the current month.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
      with exposure or not
    :return: the redis key
    """
    return f"{_authorized_tokens_redis_key_prefix(with_exposure)}:" f"{current_month().isoformat()}"


def get_authorized_tokens_redis_key_next_month(with_exposure: bool) -> str:
    """
    Generate the redis key associated with the authorized analytics tokens for the next month.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
      with exposure or not
    :return: the redis key
    """
    return f"{_authorized_tokens_redis_key_prefix(with_exposure)}:" f"{next_month().isoformat()}"


def _authorized_tokens_redis_key_prefix(with_exposure: bool) -> str:
    """
    Generate the redis key prefix.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
      with exposure or not
    :return: the prefix for the redis key.
    """
    return f"authorized-{'with-exposure' if with_exposure else 'without-exposure'}"


async def enqueue_operational_info(operational_info: OperationalInfo) -> None:
    """
    Stores the given operational info in the queue that will later
     be processed by the celery workers.
    :param operational_info: The operational info to be stored.
    """
    await managers.analytics_redis.rpush(
        config.OPERATIONAL_INFO_QUEUE_KEY, json.dumps(operational_info.to_dict())
    )
