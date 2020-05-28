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

import asyncio
import json
import logging
from json import JSONDecodeError

from marshmallow import ValidationError as MarshmallowValidationError
from mongoengine import ValidationError as MongoengineValidationError

from immuni_analytics.celery import celery_app
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.models.exposure_data import ExposurePayload
from immuni_common.core.exceptions import ImmuniException

_LOGGER = logging.getLogger(__name__)


@celery_app.task()
def store_ingested_data() -> None:  # pragma: no cover
    """
     Celery doesn't support async functions, so we wrap it around asyncio.run.
     """
    asyncio.run(_store_ingested_data())


class InvalidFormatException(ImmuniException):
    """Raised when the ingested date format is invalid"""


async def _store_ingested_data() -> None:
    """
    Retrieve up to a fixed number of ingested data and save it into mongo.
    If something goes wrong push the data into the error queue.
    """
    _LOGGER.info("Data ingestion started.",)
    pipe = managers.analytics_redis.pipeline()
    pipe.lrange(config.ANALYTICS_QUEUE_KEY, 0, config.MAX_INGESTED_ELEMENTS - 1)
    pipe.ltrim(config.ANALYTICS_QUEUE_KEY, config.MAX_INGESTED_ELEMENTS, -1)
    ingested_data = (await pipe.execute())[0]

    bad_format_data = []
    exposure_data = []

    for element in ingested_data:
        try:
            exposure_payload = extract_payload(element)
        except (
            MongoengineValidationError,
            MarshmallowValidationError,
            JSONDecodeError,
            InvalidFormatException,
        ):
            bad_format_data.append(element)
            continue

        exposure_data.append(exposure_payload)

    if exposure_data:
        ExposurePayload.objects.insert(exposure_data)
    if bad_format_data:
        _LOGGER.warning(
            "Found ingested data with bad format", extra={"bad_format_data": len(bad_format_data)}
        )
        managers.analytics_redis.rpush(config.ANALYTICS_ERRORS_QUEUE_KEY, *bad_format_data)

    queue_length = await managers.analytics_redis.llen(config.ANALYTICS_QUEUE_KEY)
    _LOGGER.info(
        "Data ingestion completed.",
        extra={"ingested_data": len(exposure_data), "ingestion_queue_length": queue_length},
    )


def extract_payload(exposure_payload_dict: str) -> ExposurePayload:
    """
    Convert and validate a dictionary into an ExposurePayload

    :param exposure_payload_dict: a dictionary to be converted into ExposurePayload
    :raises: InvalidFormatException
    :return: the converted ExposurePayload
    """
    json_decoded = json.loads(exposure_payload_dict)
    if not (
        json_decoded.get("version", None) == 1 and (payload := json_decoded.get("payload", None))
    ):
        raise InvalidFormatException()

    exposure_payload = ExposurePayload.from_dict(payload)
    exposure_payload.validate()

    return exposure_payload
