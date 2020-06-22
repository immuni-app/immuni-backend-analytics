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

from datetime import datetime, timedelta

from immuni_analytics.celery.scheduled.app import celery_app
from immuni_analytics.core import config
from immuni_analytics.models.exposure_data import ExposurePayload
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_analytics.monitoring.celery import DELETED_EXPOSURE_PAYLOAD, DELETED_OPERATIONAL_INFO


@celery_app.task()
def delete_old_data() -> None:
    """
    Delete all ExposurePayload and OperationalInfo objects older than the configured retention days.
    """
    reference_date = datetime.utcnow() - timedelta(days=config.DATA_RETENTION_DAYS)

    if deleted_exposure_payloads := ExposurePayload.delete_older_than(reference_date):
        DELETED_EXPOSURE_PAYLOAD.inc(deleted_exposure_payloads)

    if deleted_operational_infos := OperationalInfo.delete_older_than(reference_date):
        DELETED_OPERATIONAL_INFO.inc(deleted_operational_infos)
