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
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

import jwt
from aiohttp import ClientError, ClientSession

from immuni_analytics.core import config
from immuni_analytics.helpers.request import (
    BadFormatRequestError,
    ServerUnavailableError,
    post_with_retry,
)
from immuni_analytics.models.device_check import DeviceCheckData

_LOGGER = logging.getLogger(__name__)

_DEVICE_CHECK_GET_BITS_URL = f"{config.APPLE_DEVICE_CHECK_URL}/query_two_bits"
_DEVICE_CHECK_SET_BITS_URL = f"{config.APPLE_DEVICE_CHECK_URL}/update_two_bits"


class DeviceCheckApiError(Exception):
    """Raised when an error occurs while calling the DeviceCheck API."""


def _generate_device_check_jwt() -> str:
    """
    Create an authorization token to query the DeviceCheck API.

    :return: a jwt token as string.
    """
    return jwt.encode(
        payload={"iss": config.APPLE_TEAM_ID, "iat": int(datetime.utcnow().timestamp())},
        key=config.APPLE_CERTIFICATE_KEY,
        algorithm="ES256",
        headers={"kid": config.APPLE_KEY_ID},
    ).decode("utf-8")


def _generate_headers() -> Dict[str, str]:
    """
    Create the headers to be sent to the DeviceCheck API.

    :return: a dictionary containing the Authorization header.
    """
    return {"Authorization": f"Bearer {_generate_device_check_jwt()}"}


def _generate_common_payload() -> Dict[str, Any]:
    """
    Create the common part of the payload to be sent to the DeviceCheckApi.

    :return: a dictionary containing the transaction id and the current timestamp in milliseconds.
    """
    return {
        "transaction_id": str(uuid.uuid4()),
        # timestamp in millisecond
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
    }


async def fetch_device_check_bits(token: str) -> DeviceCheckData:
    """
    Fetch the two bits from the DeviceCheck API.

    :param token: the base64 encoded device token.
    :return: a DeviceCheckData object representing the device bit state.
    """

    payload = {
        **_generate_common_payload(),
        "device_token": token,
    }

    async with ClientSession() as session:
        try:
            response = await post_with_retry(
                session, url=_DEVICE_CHECK_GET_BITS_URL, json=payload, headers=_generate_headers()
            )
        except BadFormatRequestError as exc:
            _LOGGER.warning("The DeviceCheck API returned a 400 error.", extra={"payload": payload})
            raise DeviceCheckApiError() from exc
        except (ClientError, TimeoutError, ServerUnavailableError) as exc:
            _LOGGER.warning("The DeviceCheck API is not available.", extra={"payload": payload})
            raise DeviceCheckApiError() from exc

        # if the bits have never been set the api returns 200 with a plain string
        # instead of a json response.
        if response.decode("utf-8") == "Failed to find bit state":
            return DeviceCheckData(bit0=False, bit1=False, last_update_time=None)

        return DeviceCheckData(**(json.loads(response)))


async def set_device_check_bits(token: str, *, bit0: bool, bit1: bool) -> None:
    """
    Set the two DeviceCheck bits for the given device.

    :param token: the base64 encoded device token.
    :param bit0: the first DeviceCheck bit to set.
    :param bit1: the second DeviceCheck bit to set.
    """
    payload = {
        **_generate_common_payload(),
        "device_token": token,
        "bit0": bit0,
        "bit1": bit1,
    }

    async with ClientSession() as session:
        try:
            await post_with_retry(
                session, url=_DEVICE_CHECK_SET_BITS_URL, json=payload, headers=_generate_headers()
            )
        except BadFormatRequestError as exc:
            _LOGGER.warning("The DeviceCheck API returned a 400 error", extra={"payload": payload})
            raise DeviceCheckApiError() from exc
        except (ClientError, TimeoutError, ServerUnavailableError) as exc:
            _LOGGER.warning("The DeviceCheck API is not available.", extra={"payload": payload})
            raise DeviceCheckApiError() from exc
