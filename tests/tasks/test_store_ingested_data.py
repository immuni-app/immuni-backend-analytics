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

import json
from typing import Any, Callable, Dict, List
from unittest.mock import MagicMock, call, patch

from pytest import mark

from immuni_analytics.celery.scheduled.tasks.store_exposure_payloads import _store_exposure_payloads
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.models.exposure_data import ExposurePayload


@mark.parametrize(
    "n_elements, max_ingested_elements",
    tuple((e, m) for e in range(0, 50, 10) for m in range(10, 50, 25)),
)
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_ingest_data(
    logger_info: MagicMock,
    n_elements: int,
    max_ingested_elements: int,
    generate_redis_data: Callable[..., Dict[str, Any]],
) -> None:
    with patch(
        "immuni_analytics.celery.scheduled.tasks.store_exposure_payloads.config."
        "EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS",
        max_ingested_elements,
    ):
        if n_elements > 0:
            await managers.analytics_redis.rpush(
                config.EXPOSURE_PAYLOAD_QUEUE_KEY,
                *[json.dumps(d) for d in generate_redis_data(length=n_elements)]
            )
        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        ingested_data = min(n_elements, config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS)

        assert ExposurePayload.objects.count() == ingested_data
        remaining_elements = max(0, n_elements - config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS)
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={
                        "ingested_data": ingested_data,
                        "ingestion_queue_length": remaining_elements,
                    },
                ),
            ],
            any_order=False,
        )


@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_json_error(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    generate_redis_data: Callable[..., Dict[str, Any]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 2):
        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY,
            "non_json_string",
            *[json.dumps(d) for d in generate_redis_data(length=3)]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 1

        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 1
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 1, "ingestion_queue_length": 2},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_called_once_with(
            "Found ingested data with bad format.", extra={"bad_format_data": 1}
        )


@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_validation_error(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    generate_redis_data: Callable[..., List[Dict[str, Any]]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 2):
        redis_data = generate_redis_data(length=3)
        redis_data[0]["payload"]["exposure_detection_summaries"][0]["date"] = "2020-11-123"

        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY, *[json.dumps(d) for d in redis_data]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 1

        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 1
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 1, "ingestion_queue_length": 1},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_called_once_with(
            "Found ingested data with bad format.", extra={"bad_format_data": 1}
        )


@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_wrong_exposure_data_error(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    generate_redis_data: Callable[..., List[Dict[str, Any]]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 5):
        redis_data = generate_redis_data(length=5)
        del redis_data[0]["version"]
        redis_data[1]["version"] = 2
        del redis_data[2]["payload"]
        del redis_data[3]["payload"]["province"]
        del redis_data[4]["payload"]["exposure_detection_summaries"]

        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY, *[json.dumps(d) for d in redis_data]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 0

        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 5
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 0, "ingestion_queue_length": 0},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_called_once_with(
            "Found ingested data with bad format.", extra={"bad_format_data": 5}
        )


@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_empty_exposure_info_summary(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    generate_redis_data: Callable[..., List[Dict[str, Any]]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 1):
        redis_data = generate_redis_data(length=1)
        redis_data[0]["payload"]["exposure_detection_summaries"] = []

        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY, *[json.dumps(d) for d in redis_data]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 1

        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 0
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 1, "ingestion_queue_length": 0},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_not_called()


@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_empty_exposure_info(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    generate_redis_data: Callable[..., List[Dict[str, Any]]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 1):
        redis_data = generate_redis_data(length=1)
        redis_data[0]["payload"]["exposure_detection_summaries"][0]["exposure_info"] = []

        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY, *[json.dumps(d) for d in redis_data]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 1

        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 0
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 1, "ingestion_queue_length": 0},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_not_called()


@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_missing_symptoms_started_on(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    generate_redis_data: Callable[..., List[Dict[str, Any]]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 1):
        redis_data = generate_redis_data(length=1)
        del redis_data[0]["payload"]["symptoms_started_on"]

        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY, *[json.dumps(d) for d in redis_data]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 1

        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 0
        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 1, "ingestion_queue_length": 0},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_not_called()


@mark.parametrize("value", ["asd", [], {}, "2020-123-01", "2020-01-123"])
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.warning")
@patch("immuni_analytics.celery.scheduled.tasks.store_exposure_payloads._LOGGER.info")
async def test_wrong_symptoms_started_on(
    logger_info: MagicMock,
    logger_warning: MagicMock,
    value: Any,
    generate_redis_data: Callable[..., List[Dict[str, Any]]],
) -> None:
    with patch("immuni_analytics.core.config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS", 5):
        redis_data = generate_redis_data(length=1)
        redis_data[0]["payload"]["symptoms_started_on"] = value

        await managers.analytics_redis.rpush(
            config.EXPOSURE_PAYLOAD_QUEUE_KEY, *[json.dumps(d) for d in redis_data]
        )

        assert ExposurePayload.objects.count() == 0

        await _store_exposure_payloads()

        assert ExposurePayload.objects.count() == 0
        assert (await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY)) == 1

        assert logger_info.call_count == 2
        logger_info.assert_has_calls(
            [
                call("Store exposure payload periodic task started."),
                call(
                    "Store exposure payload periodic task completed.",
                    extra={"ingested_data": 0, "ingestion_queue_length": 0},
                ),
            ],
            any_order=False,
        )
        logger_warning.assert_called_once_with(
            "Found ingested data with bad format.", extra={"bad_format_data": 1}
        )
