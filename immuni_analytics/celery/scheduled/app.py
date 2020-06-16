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
from typing import Any, List, Tuple

from celery.schedules import crontab
from celery.signals import worker_process_init, worker_process_shutdown
from croniter import croniter

from immuni_analytics.celery.scheduled import tasks
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_common.celery import CeleryApp, Schedule


# pylint: disable=import-outside-toplevel
# pylint: disable=cyclic-import
def _get_schedules() -> Tuple[Schedule, ...]:
    """
    Get static scheduling of tasks.
    # NOTE: Tasks need to be imported locally, so as to avoid cyclic dependencies.
    :return: the tuple of tasks schedules.
    """

    from immuni_analytics.celery.scheduled.tasks.store_exposure_payloads import (
        store_exposure_payloads,
    )
    from immuni_analytics.celery.scheduled.tasks.delete_old_data import delete_old_data

    # TODO: move to common
    def to_crontab_args(crontab_entry: str) -> List[str]:
        return [",".join(map(str, x)) for x in croniter(crontab_entry).expanded]

    return (
        Schedule(
            task=store_exposure_payloads,
            when=crontab(*to_crontab_args(config.STORE_INGESTED_DATA_PERIODICITY)),
        ),
        Schedule(
            task=delete_old_data,
            when=crontab(*to_crontab_args(config.DELETE_OLD_DATA_PERIODICITY)),
        ),
    )


# pylint: disable=duplicate-code
@worker_process_init.connect
def worker_process_init_listener_exposure_payload(**kwargs: Any) -> None:
    """
    Listener on worker initialization to properly initialize the project's managers.

    :param kwargs: the keyword arguments passed by Celery, ignored in this case.
    """

    asyncio.run(managers.initialize(initialize_mongo=True))


@worker_process_shutdown.connect
def worker_process_shutdown_listener_exposure_payload(**kwargs: Any) -> None:
    """
    Listener on worker shutdown to properly cleanup the project's managers.

    :param kwargs: the keyword arguments passed by Celery, ignored in this case.
    """
    asyncio.run(managers.teardown())


celery_app = CeleryApp(
    service_dir_name="immuni_analytics.celery.exposure_payload",
    broker_redis_url=config.CELERY_BROKER_REDIS_URL_SCHEDULED,
    always_eager=config.CELERY_ALWAYS_EAGER,
    schedules_function=_get_schedules,
    tasks_module=tasks,
)
