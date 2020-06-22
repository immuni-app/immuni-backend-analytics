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

import json
import logging
from typing import List

from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.date_utils import current_month, next_month
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_analytics.monitoring.api import OPERATIONAL_INFO_ENQUEUED

_LOGGER = logging.getLogger(__name__)


def get_upload_authorization_member_for_current_month(with_exposure: bool) -> str:
    """
    Generate the redis key associated with the authorized analytics tokens for the current month.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
      with exposure or not.
    :return: the redis key.
    """
    return f"{current_month().isoformat()}:{int(with_exposure)}"


def get_upload_authorization_member_for_next_month(with_exposure: bool) -> str:
    """
    Generate the redis key associated with the authorized analytics tokens for the next month.

    :param with_exposure: whether the key is associated to the tokens allowed to perform an upload
      with exposure or not.
    :return: the redis key.
    """
    return f"{next_month().isoformat()}:{int(with_exposure)}"


def get_all_authorizations_for_upload() -> List[str]:
    """
    Get all the members needed to authorize an analytics token for the current and next month.

    :return: the list of string members.
    """
    return [
        get_upload_authorization_member_for_current_month(with_exposure=True),
        get_upload_authorization_member_for_current_month(with_exposure=False),
        get_upload_authorization_member_for_next_month(with_exposure=True),
        get_upload_authorization_member_for_next_month(with_exposure=False),
    ]


async def is_upload_authorized_for_token(analytics_token: str) -> bool:
    """
    Check if an analytics token is authorized for the current month.

    :param analytics_token: the analytics token to check.
    :return: True if the analytics token is authorized, False otherwise.
    """
    members = await managers.analytics_redis.smembers(analytics_token)
    return members and (
        get_upload_authorization_member_for_current_month(with_exposure=True) in members
        or get_upload_authorization_member_for_current_month(with_exposure=False) in members
    )


async def enqueue_operational_info(operational_info: OperationalInfo) -> None:
    """
    Store the given operational info in the queue eventually processed by the celery workers.

    :param operational_info: the operational info to store.
    """
    await managers.analytics_redis.rpush(
        config.OPERATIONAL_INFO_QUEUE_KEY, json.dumps(operational_info.to_dict())
    )
    _LOGGER.info("Successfully enqueued operational info.")
    OPERATIONAL_INFO_ENQUEUED.labels(operational_info.platform.value).inc()
