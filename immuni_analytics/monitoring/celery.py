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

from prometheus_client.metrics import Counter

from immuni_common.monitoring.core import NAMESPACE, Subsystem

AUTHORIZE_ANALYTICS_TOKEN_FIRST_STEP_BEGIN = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="authorize_analytics_token_first_step_begin",
    documentation="Number of analytics tokens which started the authorization first step.",
)

AUTHORIZE_ANALYTICS_TOKEN_SECOND_STEP_BEGIN = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="authorize_analytics_token_second_step_begin",
    documentation="Number of analytics tokens which started the authorization second step.",
)

AUTHORIZE_ANALYTICS_TOKEN_THIRD_STEP_BEGIN = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="authorize_analytics_token_third_step_begin",
    documentation="Number of analytics tokens which started the authorization third step.",
)

AUTHORIZE_ANALYTICS_TOKEN_AUTHORIZED = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="authorize_analytics_token_authorized",
    documentation="Number of analytics tokens successfully authorized.",
)

AUTHORIZE_ANALYTICS_TOKEN_BLACKLISTED = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="authorize_analytics_token_blacklisted",
    documentation="Number of analytics tokens unsuccessfully authorized.",
)

DELETED_EXPOSURE_PAYLOAD = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="deleted_exposure_payload",
    documentation="Number of deleted ExposurePayload documents.",
)

DELETED_OPERATIONAL_INFO = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="deleted_operational_info",
    documentation="Number of deleted OperationalInfo documents.",
)

STORED_EXPOSURE_PAYLOAD = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="stored_exposure_payload",
    documentation="Number of stored ExposurePayload documents.",
)

WRONG_EXPOSURE_PAYLOAD = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.CELERY.value,
    name="wrong_exposure_payload",
    documentation="Number of malformed ExposurePayload documents coming from the ingestion MS.",
)
