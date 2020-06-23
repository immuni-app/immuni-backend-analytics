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
from typing import Any

from celery.signals import worker_process_init, worker_process_shutdown

from immuni_analytics.celery.authorization_android import tasks
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_common.celery import CeleryApp


@worker_process_shutdown.connect
def worker_process_shutdown_listener(**kwargs: Any) -> None:  # pragma: no cover
    """
    Listener on worker shutdown to properly cleanup the project's managers.

    :param kwargs: the keyword arguments passed by Celery, ignored in this case.
    """
    asyncio.run(managers.teardown())


@worker_process_init.connect
def worker_process_init_listener(**kwargs: Any) -> None:  # pragma: no cover
    """
    Listener on worker initialization to properly initialize the project's managers.

    :param kwargs: the keyword arguments passed by Celery, ignored in this case.
    """
    asyncio.run(managers.initialize(initialize_mongo=False))


celery_app = CeleryApp(
    service_dir_name="immuni_analytics.celery.authorization_android",
    broker_redis_url=config.CELERY_BROKER_REDIS_URL_AUTHORIZATION_ANDROID,
    always_eager=config.CELERY_ALWAYS_EAGER,
    tasks_module=tasks,
)
