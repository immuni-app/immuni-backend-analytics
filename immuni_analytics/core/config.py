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

import logging

from decouple import config

from immuni_analytics.models.enums import AnalyticsQueue
from immuni_common.core.config import ENV
from immuni_common.helpers.config import load_certificate, validate_crontab
from immuni_common.models.enums import Environment

_LOGGER = logging.getLogger(__name__)


ANALYTICS_MONGO_URL = config(
    "ANALYTICS_MONGO_URL", default="mongodb://localhost:27017/immuni-analytics-dev"
)

ANALYTICS_BROKER_REDIS_URL: str = config(
    "ANALYTICS_BROKER_REDIS_URL", default="redis://localhost:6379/1"
)
ANALYTICS_QUEUE_KEY: str = config("ANALYTICS_QUEUE_KEY", default="ingested_exposure_data")
ANALYTICS_ERRORS_QUEUE_KEY: str = config(
    "ANALYTICS_ERRORS_QUEUE_KEY", default="errors_exposure_data"
)

CELERY_BROKER_REDIS_URL: str = config("CELERY_BROKER_REDIS_URL", default="redis://localhost:6379/0")
CELERY_ALWAYS_EAGER: bool = config(
    "CELERY_ALWAYS_EAGER", cast=bool, default=ENV == Environment.TESTING
)

ANALYTICS_TOKEN_SIZE: int = config("ANALYTICS_TOKEN_SIZE", cast=int, default=128)
APPLE_CERTIFICATE_KEY: str = config(
    "APPLE_CERTIFICATE_KEY", cast=load_certificate("APPLE_CERTIFICATE_KEY"), default=""
)
APPLE_DEVICE_CHECK_URL: str = config(
    "APPLE_DEVICE_CHECK_URL",
    default="https://api.devicecheck.apple.com/v1"
    if ENV == Environment.RELEASE
    else "https://api.development.devicecheck.apple.com/v1",
)
APPLE_KEY_ID: str = config("APPLE_KEY_ID", default="")
APPLE_TEAM_ID: str = config("APPLE_TEAM_ID", default="")

CELERY_WORKER_QUEUE: AnalyticsQueue = config(
    "CELERY_WORKER_QUEUE", cast=AnalyticsQueue.from_env_var, default=AnalyticsQueue.WITH_MONGO
)
DATA_RETENTION_DAYS: int = config("DATA_RETENTION_DAYS", cast=int, default=30)
MAX_INGESTED_ELEMENTS: int = config("MAX_INGESTED_ELEMENTS", cast=int, default=100)
CHECK_TIME: int = config("CHECK_TIME", cast=int, default=7)
DELETE_OLD_DATA_PERIODICITY: str = config(
    "DELETE_OLD_DATA_PERIODICITY",
    cast=validate_crontab("DELETE_OLD_DATA_PERIODICITY"),
    default="0 0 * * *",
)
READ_TIME: int = config("READ_TIME", cast=int, default=3)
SAFETY_NET_MAX_SKEW_MINUTES: int = config("SAFETY_NET_MAX_SKEW_MINUTES", cast=int, default=10)
STORE_INGESTED_DATA_PERIODICITY: str = config(
    "STORE_INGESTED_DATA_PERIODICITY",
    cast=validate_crontab("STORE_INGESTED_DATA_PERIODICITY"),
    default="* * * * *",
)
SAFETY_NET_APK_DIGEST: str = config("SAFETY_NET_APK_DIGEST", default="")
SAFETY_NET_ISSUER_HOSTNAME: str = config("SAFETY_NET_ISSUER_HOSTNAME", default="attest.android.com")
SAFETY_NET_PACKAGE_NAME: str = config(
    "SAFETY_NET_PACKAGE_NAME", default="it.ministerodellasalute.immuni"
)
