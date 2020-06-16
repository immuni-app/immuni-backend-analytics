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

from typing import Any, Dict

from immuni_analytics.celery.operational_info.app import celery_app
from immuni_analytics.models.operational_info import OperationalInfo


@celery_app.task()
def store_operational_info(operational_info: Dict[str, Any]) -> None:
    """
    Store the operational information in the database. This can only happen twice a month for each
    analytics token.

    :param operational_info: a dictionary containing the operational information
    """
    OperationalInfo.from_dict(operational_info).save()


