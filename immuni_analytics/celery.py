#    Copyright (C) 2020 Presidenza del Consiglio dei Ministri.
#    Please refer to the AUTHORS file for more information.
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <https://www.gnu.org/licenses/>.

import asyncio
from enum import Enum
from typing import Any, List, Tuple

from celery.schedules import crontab
from celery.signals import worker_process_init, worker_process_shutdown
from croniter import croniter

from immuni_analytics import tasks
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_common.celery import CeleryApp, Schedule

from immuni_analytics.tasks.route import route
import logging


class AnalyticsQueue(Enum):
    WITHOUT_MONGO = "without_mongo"
    WITH_MONGO = "with_mongo"


_LOGGER = logging.getLogger(__name__)


def _get_schedules() -> Tuple[Schedule, ...]:
    """
    Get static scheduling of tasks.
    # NOTE: Tasks need to be imported locally, so as to avoid cyclic dependencies.
    :return: the tuple of tasks schedules.
    """

    # pylint: disable=import-outside-toplevel
    # pylint: disable=cyclic-import
    from immuni_analytics.tasks.store_ingested_data import store_ingested_data

    # pylint: disable=import-outside-toplevel
    # pylint: disable=cyclic-import
    from immuni_analytics.tasks.delete_old_data import delete_old_data

    # TODO: move to common
    def to_crontab_args(crontab_entry: str) -> List[str]:
        return [",".join(map(str, x)) for x in croniter(crontab_entry).expanded]

    return (
        Schedule(
            task=store_ingested_data,
            when=crontab(*to_crontab_args(config.STORE_INGESTED_DATA_PERIODICITY)),
        ),
        Schedule(
            task=delete_old_data,
            when=crontab(*to_crontab_args(config.DELETE_OLD_DATA_PERIODICITY)),
        ),
    )


@worker_process_init.connect
def worker_process_init_listener(**kwargs: Any) -> None:
    """
    Listener on worker initialization to properly initialize the project's managers.

    :param kwargs: the keyword arguments passed by Celery, ignored in this case.
    :raises: ImmuniException
    """
    # The celery inspect needs some time to initialize correctly
    # sleep(3)
    # active_queues_lists = celery_app.control.inspect().active_queues()
    # worker_queues = [
    #     queue_info["name"] for active_queue_list in active_queues_lists.values() for queue_info in active_queue_list
    # ]
    # if len(worker_queues) != 1:
    #     raise ImmuniException("More than one queue specified for celery worker. ")

    asyncio.run(managers.initialize(initialize_mongo=True))


@worker_process_shutdown.connect
def worker_process_shutdown_listener(**kwargs: Any) -> None:
    """
    Listener on worker shutdown to properly cleanup the project's managers.

    :param kwargs: the keyword arguments passed by Celery, ignored in this case.
    """
    asyncio.run(managers.teardown())


celery_app = CeleryApp(
    service_dir_name="immuni_analytics",
    broker_redis_url=config.CELERY_BROKER_REDIS_URL,
    always_eager=config.CELERY_ALWAYS_EAGER,
    schedules_function=_get_schedules,
    routes_function=route,
    tasks_module=tasks,
)
