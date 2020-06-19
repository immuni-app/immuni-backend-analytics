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

import logging

from decouple import config

from immuni_analytics.models.enums import CeleryAppName
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
EXPOSURE_PAYLOAD_QUEUE_KEY: str = config(
    "EXPOSURE_PAYLOAD_QUEUE_KEY", default="ingested_exposure_data"
)
EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY: str = config(
    "EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY", default="errors_exposure_data"
)
OPERATIONAL_INFO_QUEUE_KEY: str = config("OPERATIONAL_INFO_QUEUE_KEY", default="operational_info")
CELERY_ALWAYS_EAGER: bool = config(
    "CELERY_ALWAYS_EAGER", cast=bool, default=ENV == Environment.TESTING
)
CELERY_BROKER_REDIS_URL_AUTHORIZATION: str = config(
    "CELERY_BROKER_REDIS_URL_AUTHORIZATION", default="redis://localhost:6379/0"
)
CELERY_BROKER_REDIS_URL_SCHEDULED: str = config(
    "CELERY_BROKER_REDIS_URL_SCHEDULED", default="redis://localhost:6379/0"
)
CELERY_APP_NAME: CeleryAppName = config(
    "CELERY_APP_NAME", cast=CeleryAppName.from_env_var, default=CeleryAppName.AUTHORIZATION
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
CHECK_TIME_SECONDS_MAX: int = config("CHECK_TIME_SECONDS_MAX", cast=int, default=10)
CHECK_TIME_SECONDS_MIN: int = config("CHECK_TIME_SECONDS_MIN", cast=int, default=7)
DATA_RETENTION_DAYS: int = config("DATA_RETENTION_DAYS", cast=int, default=30)
DEVICE_TOKEN_MAX_LENGTH: int = config("DEVICE_TOKEN_MAX_LENGTH", cast=int, default=10_000)
DELETE_OLD_DATA_PERIODICITY: str = config(
    "DELETE_OLD_DATA_PERIODICITY",
    cast=validate_crontab("DELETE_OLD_DATA_PERIODICITY"),
    default="0 0 * * *",
)
EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS: int = config(
    "EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", cast=int, default=100
)
OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS: int = config(
    "OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS", cast=int, default=100
)
READ_TIME_SECONDS_MAX: int = config("READ_TIME_SECONDS_MAX", cast=int, default=3)
READ_TIME_SECONDS_MIN: int = config("READ_TIME_SECONDS_MIN", cast=int, default=0)
REQUESTS_TIMEOUT_SECONDS: int = config("REQUESTS_TIMEOUT_SECONDS", cast=int, default=5)
SAFETY_NET_MAX_SKEW_MINUTES: int = config("SAFETY_NET_MAX_SKEW_MINUTES", cast=int, default=10)
STORE_INGESTED_DATA_PERIODICITY: str = config(
    "STORE_INGESTED_DATA_PERIODICITY",
    cast=validate_crontab("STORE_INGESTED_DATA_PERIODICITY"),
    default="* * * * *",
)
STORE_OPERATIONAL_INFO_PERIODICITY: str = config(
    "STORE_OPERATIONAL_INFO_PERIODICITY",
    cast=validate_crontab("STORE_OPERATIONAL_INFO_PERIODICITY"),
    default="* * * * *",
)
SAFETY_NET_APK_DIGEST: str = config("SAFETY_NET_APK_DIGEST", default="")
SAFETY_NET_ISSUER_HOSTNAME: str = config("SAFETY_NET_ISSUER_HOSTNAME", default="attest.android.com")
SAFETY_NET_PACKAGE_NAME: str = config(
    "SAFETY_NET_PACKAGE_NAME", default="it.ministerodellasalute.immuni"
)
SALT_LENGTH: int = config("SALT_LENGTH", cast=int, default=24)
SIGNED_ATTESTATION_MAX_LENGTH: int = config(
    "SIGNED_ATTESTATION_MAX_LENGTH", cast=int, default=10_000
)

DUMMY_REQUEST_TIMEOUT_MILLIS: int = config("DUMMY_REQUEST_TIMEOUT_MILLIS", cast=int, default=150)
DUMMY_REQUEST_TIMEOUT_SIGMA: int = config("DUMMY_REQUEST_TIMEOUT_SIGMA", cast=int, default=20)
