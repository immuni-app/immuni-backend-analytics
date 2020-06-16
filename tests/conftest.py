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

from immuni_common.helpers.tests import check_redis_url  # noqa isort:skip
from immuni_analytics.core import config
from immuni_common.helpers.tests import check_environment, check_mongo_url

from tests.fixtures.core import *  # noqa isort:skip
from tests.fixtures.exposure_data import *  # noqa isort:skip
from tests.fixtures.safety_net import *  # noqa isort:skip
from immuni_common.helpers.tests import monitoring_setup  # noqa isort:skip


check_environment()
check_mongo_url(config.ANALYTICS_MONGO_URL, "ANALYTICS_MONGO_URL")
check_redis_url(config.ANALYTICS_BROKER_REDIS_URL, "ANALYTICS_BROKER_REDIS_URL")
check_redis_url(
    config.CELERY_BROKER_REDIS_URL_AUTHORIZATION, "CELERY_BROKER_REDIS_URL_AUTHORIZATION"
)
check_redis_url(config.CELERY_BROKER_REDIS_URL_SCHEDULED, "CELERY_BROKER_REDIS_URL_SCHEDULED")
check_redis_url(
    config.CELERY_BROKER_REDIS_URL_OPERATIONAL_INFO, "CELERY_BROKER_REDIS_URL_OPERATIONAL_INFO"
)
