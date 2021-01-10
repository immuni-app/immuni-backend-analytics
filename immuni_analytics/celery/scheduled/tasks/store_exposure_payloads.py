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

import asyncio
import json
import logging
from json import JSONDecodeError

from marshmallow import ValidationError as MarshmallowValidationError
from mongoengine import ValidationError as MongoengineValidationError

from immuni_analytics.celery.scheduled.app import celery_app
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.his_external_service import invalidate_cun
from immuni_analytics.models.exposure_data import ExposurePayload
from immuni_analytics.monitoring.celery import STORED_EXPOSURE_PAYLOAD, WRONG_EXPOSURE_PAYLOAD
from immuni_common.core.exceptions import ImmuniException

_LOGGER = logging.getLogger(__name__)


class InvalidFormatException(ImmuniException):
    """
    Raised when the ingested date format is invalid.
    """


@celery_app.task()
def store_exposure_payloads() -> None:  # pragma: no cover
    """
    Celery doesn't support async functions, so we wrap it around asyncio.run.
    """
    asyncio.run(_store_exposure_payloads())


async def _store_exposure_payloads() -> None:
    """
    Retrieve up to a fixed number of exposure payload data and save it into mongo.
    If something goes wrong, push the data into the error queue.
    """
    pipe = managers.analytics_redis.pipeline()
    pipe.lrange(
        config.EXPOSURE_PAYLOAD_QUEUE_KEY, 0, config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS - 1
    )
    pipe.ltrim(config.EXPOSURE_PAYLOAD_QUEUE_KEY, config.EXPOSURE_PAYLOAD_MAX_INGESTED_ELEMENTS, -1)
    ingested_data = (await pipe.execute())[0]

    cun_to_invalidate = []
    bad_format_data = []
    exposure_data = []

    for element in ingested_data:
        try:
            json_decoded = json.loads(element)
            exposure_payload = _load_exposure_payload(json_decoded)
            cun_to_invalidate.append(_load_cun_attributes(json_decoded))
        except (
            MongoengineValidationError,
            MarshmallowValidationError,
            JSONDecodeError,
            InvalidFormatException,
        ):
            bad_format_data.append(element)
            continue

        exposure_data.append(exposure_payload)

    if n_exposure_data := len(exposure_data):
        ExposurePayload.objects.insert(exposure_data)
        STORED_EXPOSURE_PAYLOAD.inc(n_exposure_data)

    if n_bad_format_data := len(bad_format_data):
        managers.analytics_redis.rpush(config.EXPOSURE_PAYLOAD_ERRORS_QUEUE_KEY, *bad_format_data)
        _LOGGER.warning(
            "Found ingested data with bad format.", extra={"bad_format_data": n_bad_format_data}
        )
        WRONG_EXPOSURE_PAYLOAD.inc(n_bad_format_data)

    # Request to invalidate CUN through HIS service
    for cun in cun_to_invalidate:
        id_test_verification = cun.get("id_test_verification", None)
        token_sha = cun.get("token_sha", None)
        if id_test_verification and token_sha:
            invalidate_cun(cun_sha=token_sha, id_test_verification=id_test_verification)
            _LOGGER.info(
                "Calling HIS service to invalidate CUN.",
                extra={"cun_sha": token_sha, "id_test_verification": id_test_verification},
            )

    queue_length = await managers.analytics_redis.llen(config.EXPOSURE_PAYLOAD_QUEUE_KEY)
    _LOGGER.info(
        "Store exposure payload periodic task completed.",
        extra={"ingested_data": n_exposure_data, "ingestion_queue_length": queue_length},
    )


def _load_exposure_payload(json_decoded: dict) -> ExposurePayload:
    """
    Convert and validate a dictionary into an ExposurePayload object.

    :param json_decoded: the dictionary to be converted into an ExposurePayload object.
    :return: the converted ExposurePayload object.
    :raises: InvalidFormatException.
    """
    if not (
        json_decoded.get("version", None) == 1 and (payload := json_decoded.get("payload", None))
    ):
        raise InvalidFormatException()

    exposure_payload = ExposurePayload.from_dict(payload)
    exposure_payload.validate()

    return exposure_payload


def _load_cun_attributes(json_decoded: dict) -> dict:
    """
    Extract from a dictionary two attributes and add to to a new dictionary.

    :param json_decoded: the dictionary from which to extract attributes.
    :return: a dict with two keys.
    :raises: InvalidFormatException.
    """
    if not (
        json_decoded.get("version", None) == 1 and (payload := json_decoded.get("payload", None))
    ):
        raise InvalidFormatException()

    id_test_verification = payload.get("id_test_verification", None)
    token_sha = payload.get("token_sha", None)

    return dict(id_test_verification=id_test_verification, token_sha=token_sha)
