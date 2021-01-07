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
from immuni_common.core.exceptions import ApiException

from immuni_analytics.core import config

_LOGGER = logging.getLogger(__name__)


def invalidate_cun(cun_sha: str, id_transaction: str) -> None:
    """
    The request should use mutual TLS authentication.

    :param cun_sha: the unique national code in sha256 format released by the HIS.
    :param id_transaction: the id of the transaction returned from HIS service.
    """
    #remote_url = f"https://{config.HIS_INVALIDATE_EXTERNAL_URL}"
    remote_url = f"http://{config.HIS_INVALIDATE_EXTERNAL_URL}"
    body = dict(cun=cun_sha, id_transaction=id_transaction)

    _LOGGER.info("Requesting invalidation with external HIS service.", extra=body)

    response = requests.post(
        remote_url,
        json=body
        #verify=config.HIS_SERVICE_CA_BUNDLE,
        #cert=config.HIS_SERVICE_CERTIFICATE,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise ApiException

