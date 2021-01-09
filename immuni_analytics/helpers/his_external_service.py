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

from __future__ import annotations

import logging

import requests

from immuni_analytics.core import config
from immuni_common.core.exceptions import (
    ApiException,
    OtpCollisionException,
    SchemaValidationException,
    UnauthorizedOtpException,
)

_LOGGER = logging.getLogger(__name__)


def invalidate_cun(cun_sha: str, id_test_verification: str) -> None:
    """
    Invalidate the authorized CUN through HIS external service.
    The request should use mutual TLS authentication.

    :param cun_sha: the unique national code in sha256 format released by the HIS.
    :param id_test_verification: the id of the test returned from HIS service.
    """
    remote_url = f"https://{config.HIS_INVALIDATE_EXTERNAL_URL}"

    body = dict(cun=cun_sha, id_test_verification=id_test_verification)

    _LOGGER.info("Requesting invalidation with external HIS service.", extra=body)

    response = requests.post(
        remote_url,
        json=body,
        verify=config.HIS_SERVICE_CA_BUNDLE,
        cert=config.HIS_SERVICE_CERTIFICATE,
    )
    if response.status_code == 400:
        _LOGGER.error("Response %d received from external service.",
                      response.status_code, extra=response.json())
        raise SchemaValidationException
    elif response.status_code == 401:
        _LOGGER.error("Response %d received from external service.",
                      response.status_code, extra=response.json())
        raise UnauthorizedOtpException
    elif response.status_code == 409:
        _LOGGER.error("Response %d received from external service.",
                      response.status_code, extra=response.json())
        raise OtpCollisionException

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as msg_error:
        _LOGGER.error(msg_error)
        raise ApiException from msg_error

    json_response = response.json()
    _LOGGER.info("Response received from external service.", extra=json_response)
