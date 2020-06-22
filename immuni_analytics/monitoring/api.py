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

# NOTE: To monitor uploads / OTP request, adding the dummy and province information is important.
#  The currently existing metric "REQUESTS_LATENCY" is not enough, and adding such labels to all
#  requests would be inappropriate, since meaningless for most of them.
#  Dedicated metrics are added instead.

OPERATIONAL_INFO_REQUESTS = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.API.value,
    name="operational_info_requests",
    labelnames=("dummy", "platform", "http_status"),
    documentation="Number of operational info requests the server responded to.",
)

OPERATIONAL_INFO_ANDROID_REUSED_SALT = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.API.value,
    name="operational_info_android_reused_salt",
    labelnames=("after_verification",),
    documentation="Number of Android operational info requests using an already used salt.",
)

OPERATIONAL_INFO_ENQUEUED = Counter(
    namespace=NAMESPACE,
    subsystem=Subsystem.API.value,
    name="operational_info_enqueued",
    labelnames=("platform",),
    documentation="Number of operational info requests enqueued.",
)
