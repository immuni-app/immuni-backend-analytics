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

from immuni_analytics.apis import analytics
from immuni_analytics.core.managers import managers
from immuni_common.sanic import create_app, run_app

sanic_app = create_app(
    api_title="Analytics Service",
    api_description="The Analytics Service provides an API to the Mobile Clients for uploading"
    " certain data without identifying users, both during regular operations"
    " and especially when a match is found between a TEK Chunk and the RPIs in"
    " the RPI Database. Collecting these data is crucial to spotting anomalies"
    " in the system, as well as being able to check how many users are being"
    " notified. The National Healthcare System needs this information to"
    " operate Immuni effectively.",
    blueprints=(analytics.bp,),
    managers=managers,
)

if __name__ == "__main__":  # pragma: no cover
    run_app(sanic_app)
