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

from datetime import date
from typing import Any, Callable, Dict
from unittest.mock import MagicMock, call, patch

from pytest import mark

from immuni_analytics.celery.scheduled.tasks.store_operational_info import _store_operational_info
from immuni_analytics.core import config
from immuni_analytics.helpers.redis import enqueue_operational_info
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform

TEST_OPERATIONAL_INFO = OperationalInfo(
    platform=Platform.IOS,
    province="FC",
    exposure_permission=True,
    bluetooth_active=True,
    notification_permission=True,
    exposure_notification=True,
    last_risky_exposure_on=date.fromisoformat("2020-01-01"),
)


@mark.parametrize(
    "n_elements, max_ingested_elements",
    tuple((e, m) for e in range(0, 50, 10) for m in range(10, 50, 25)),
)
@patch("immuni_analytics.celery.scheduled.tasks.store_operational_info._LOGGER.info")
async def test_ingest_data(
    logger_info: MagicMock,
    n_elements: int,
    max_ingested_elements: int,
    generate_redis_data: Callable[..., Dict[str, Any]],
) -> None:
    with patch(
        "immuni_analytics.celery.scheduled.tasks.store_exposure_payloads.config."
        "OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS",
        max_ingested_elements,
    ):
        for _ in range(n_elements):
            await enqueue_operational_info(TEST_OPERATIONAL_INFO)

        assert OperationalInfo.objects.count() == 0

        await _store_operational_info()

        stored_data = min(n_elements, config.OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS)
        remaining_elements = max(0, n_elements - config.OPERATIONAL_INFO_MAX_INGESTED_ELEMENTS)

        assert OperationalInfo.objects.count() == stored_data
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store operational info periodic task started."),
                call(
                    "Store operational info periodic task completed.",
                    extra={
                        "stored_data": stored_data,
                        "operational_info_queue_length": remaining_elements,
                    },
                ),
            ],
            any_order=False,
        )


@mark.parametrize(
    "operational_info",
    [
        OperationalInfo(
            platform=Platform.IOS,
            province="FC",
            exposure_permission=True,
            bluetooth_active=True,
            notification_permission=True,
            exposure_notification=True,
            last_risky_exposure_on=date.fromisoformat("2020-01-01"),
        ),
        OperationalInfo(
            platform=Platform.IOS,
            province="FC",
            exposure_permission=False,
            bluetooth_active=True,
            notification_permission=True,
            exposure_notification=True,
            last_risky_exposure_on=date.fromisoformat("2020-01-01"),
        ),
        OperationalInfo(
            platform=Platform.ANDROID,
            province="FC",
            exposure_permission=True,
            bluetooth_active=True,
            notification_permission=False,
            exposure_notification=True,
            last_risky_exposure_on=date.fromisoformat("2020-01-01"),
        ),
        OperationalInfo(
            platform=Platform.IOS,
            province="FC",
            exposure_permission=False,
            bluetooth_active=False,
            notification_permission=False,
            exposure_notification=False,
            last_risky_exposure_on=None,
        ),
    ],
)
async def test_correctly_saved_operational_info(operational_info: OperationalInfo) -> None:
    await enqueue_operational_info(operational_info)

    await _store_operational_info()

    saved_operational_info = list(OperationalInfo.objects())
    assert len(saved_operational_info) == 1
    assert saved_operational_info[0].to_dict() == operational_info.to_dict()
