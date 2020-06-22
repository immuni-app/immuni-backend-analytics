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

import asyncio
import json
import logging
from collections import Counter
from typing import Dict

from immuni_analytics.celery.scheduled.app import celery_app
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_analytics.monitoring.api import OPERATIONAL_INFO_ENQUEUED

_LOGGER = logging.getLogger(__name__)


@celery_app.task()
def store_operational_info() -> None:  # pragma: no cover
    """
    Celery doesn't support async functions, so we wrap it around asyncio.run.
    """
    asyncio.run(_store_operational_info())


async def _store_operational_info() -> None:
    """
    Retrieve up to a fixed number of operational info and save it into mongo.
    """

    _LOGGER.info("Store operational info periodic task started.")
    pipe = managers.analytics_redis.pipeline()
    pipe.lrange(
        config.OPERATIONAL_INFO_QUEUE_KEY, 0, config.OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS - 1
    )
    pipe.ltrim(config.OPERATIONAL_INFO_QUEUE_KEY, config.OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS, -1)
    operational_info_list = (await pipe.execute())[0]

    operational_info_documents = [
        OperationalInfo.from_dict(json.loads(element)) for element in operational_info_list
    ]

    if operational_info_documents:
        OperationalInfo.objects.insert(operational_info_documents)
        count_per_platform: Dict[str, int] = Counter(
            document.platform.value for document in operational_info_documents
        )
        for platform, count in count_per_platform.items():
            # NOTE: decrementing together to better show it has been done in the same tasks.
            OPERATIONAL_INFO_ENQUEUED.labels(platform).dec(count)

    queue_length = await managers.analytics_redis.llen(config.OPERATIONAL_INFO_QUEUE_KEY)
    _LOGGER.info(
        "Store operational info periodic task completed.",
        extra={
            "stored_data": len(operational_info_documents),
            "operational_info_queue_length": queue_length,
        },
    )
