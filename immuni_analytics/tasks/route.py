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


def route():
    from immuni_analytics.celery import AnalyticsQueue
    from immuni_analytics.tasks.authorize_analytics_token import authorize_analytics_token
    from immuni_analytics.tasks.delete_old_data import delete_old_data
    from immuni_analytics.tasks.store_ingested_data import store_ingested_data
    from immuni_analytics.tasks.store_operational_info import store_operational_info

    return {
        authorize_analytics_token.name: dict(queue=AnalyticsQueue.WITHOUT_MONGO.value),
        delete_old_data.name: dict(queue=AnalyticsQueue.WITH_MONGO.value),
        store_ingested_data.name: dict(queue=AnalyticsQueue.WITH_MONGO.value),
        store_operational_info.name: dict(queue=AnalyticsQueue.WITH_MONGO.value),
    }
