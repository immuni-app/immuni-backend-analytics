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

from datetime import datetime, timedelta
from typing import Callable
from unittest.mock import MagicMock, patch

from celery import Celery
from freezegun import freeze_time

from immuni_analytics.celery.exposure_payload.tasks.delete_old_exposure_payloads import (
    delete_old_exposure_payloads,
)
from immuni_analytics.core import config
from immuni_analytics.models.exposure_data import ExposurePayload


@patch("immuni_analytics.tasks.delete_old_data._LOGGER.info")
@patch("immuni_analytics.models.exposure_data._LOGGER.info")
async def test_delete_old_data(
    model_logger_info: MagicMock,
    task_logger_info: MagicMock,
    generate_mongo_data: Callable[..., None],
    setup_celery_app: Celery,
) -> None:
    with patch("immuni_analytics.core.config.DATA_RETENTION_DAYS", 15):
        reference_date = datetime(2020, 2, 20)
        with freeze_time(reference_date - timedelta(days=config.DATA_RETENTION_DAYS)):
            generate_mongo_data(15)

        with freeze_time(reference_date + timedelta(seconds=1)):
            generate_mongo_data(10)

            assert ExposurePayload.objects.count() == 25

            delete_old_exposure_payloads.delay()

            assert ExposurePayload.objects.count() == 10
        task_logger_info.assert_called_once_with("Data deletion started.")
        model_logger_info.assert_called_once_with(
            "ExposurePayload documents deletion completed.",
            extra={
                "n_deleted": 15,
                "created_before": (
                    reference_date
                    + timedelta(seconds=1)
                    - timedelta(days=config.DATA_RETENTION_DAYS)
                ).isoformat(),
            },
        )
