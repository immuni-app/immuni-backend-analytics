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

import base64
import binascii
import json
import logging
from datetime import datetime, timedelta
from hashlib import sha256
from json import JSONDecodeError
from typing import Any, Dict, List

import certvalidator
import jwt
from certvalidator import CertificateValidator
from jwt import DecodeError
from OpenSSL import crypto

from immuni_analytics.core import config
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.core.exceptions import ImmuniException

_ISSUER_HOSTNAME = "attest.android.com"
_PACKAGE_NAME = "it.ministerodellasalute.immuni"

_LOGGER = logging.getLogger(__name__)


def get_redis_key(salt: str) -> str:
    """
    Retrieve the redis key for a given salt.

    :param salt: the salt corresponding to a request.
    :return: the redis key containing the salt.
    """
    return f"~safetynet-used-salt:{salt}"


class SafetyNetVerificationError(ImmuniException):
    """Raised when one of the steps in the verification fails."""


def _get_jws_part(jws_token: str, index: int) -> str:
    """
    Split the jws token in the its different parts and return the specified one.

    :param jws_token: the jws_token to split.
    :param index: the jws_token part to retrieves.
    :raises: ValueError, IndexError
    :return: the jws_token part specified by index.
    """

    if len(parts := jws_token.split(".")) == 3:
        return parts[index]

    raise ValueError()


def _parse_jws_part(jws_part: str) -> Dict[str, Any]:
    """
    Parse a base64 jsw part, adding padding if necessary, into a dictionary.

    :param jws_part: the base string to b64decode.
    :return: the decoded string.
    """
    missing_padding = len(jws_part) % 4
    if missing_padding != 0:
        jws_part += "=" * (4 - missing_padding)

    return json.loads(base64.b64decode(jws_part).decode())


def _get_jws_header(jws_token: str) -> Dict[str, Any]:
    """
    Retrieve the header of a jws token.

    :param jws_token: the jws token to get the header from.
    :return: the jws token header.
    """
    try:
        header = _parse_jws_part(_get_jws_part(jws_token, 0))
    except (JSONDecodeError, binascii.Error, IndexError, ValueError) as exc:
        _LOGGER.warning(
            "Could not retrieve header from jws token.",
            extra=dict(error=str(exc), jws_token=jws_token),
        )
        raise SafetyNetVerificationError()
    return header


def _get_jws_payload(jws_token: str) -> Dict[str, Any]:
    """
    Retrieve the payload of a jws token.

    :param jws_token: the jws token to get the payload from.
    :return: the jws token payload.
    """
    try:
        return _parse_jws_part(_get_jws_part(jws_token, 1))
    except (JSONDecodeError, binascii.Error, IndexError, ValueError) as exc:
        _LOGGER.warning(
            "Could not retrieve payload from jws token.",
            extra=dict(error=str(exc), jws_token=jws_token),
        )
        raise SafetyNetVerificationError()


def _get_certificates(header: Dict[str, Any]) -> List[bytes]:
    try:
        certificates_string = header["x5c"]
    except KeyError:
        _LOGGER.warning(
            "Could not retrieve certificates from jws header.",
            extra=dict(header=header),
        )
        raise SafetyNetVerificationError()

    try:
        certificates = [base64.b64decode(c) for c in certificates_string]
    except binascii.Error as exc:
        _LOGGER.warning(
            "Could not decode jws header certificates.",
            extra=dict(error=str(exc), certificates_string=certificates_string),
        )
        raise SafetyNetVerificationError()

    return certificates


def _get_leaf_certificate_x509(leaf_certificate_bytes: bytes):
    try:
        return crypto.load_certificate(crypto.FILETYPE_ASN1, leaf_certificate_bytes)
    except certvalidator.errors.ValidationError as exc:
        _LOGGER.warning(
            "Could not load the leaf certificate.",
            extra=dict(error=str(exc), leaf_certificate_bytes=leaf_certificate_bytes),
        )
        raise SafetyNetVerificationError()


def _validate_certificates(
        leaf_certificate_x509: crypto.X509,
        other_certificates_bytes: List[bytes]
) -> None:
    """
    Validate the SSL certificate chain and use SSL hostname matching to verify that the leaf
    certificate was issued to the _ISSUER_HOSTNAME.

    :param leaf_certificate_x509: the leaf certificate as crypto.x509 object.
    :param other_certificates_bytes: the other certificates in the chain, as list of bytes.
    """
    try:
        validator = CertificateValidator(leaf_certificate_x509, other_certificates_bytes)
        validator.validate_tls(_ISSUER_HOSTNAME)
    except certvalidator.errors.ValidationError as exc:
        _LOGGER.warning(
            "Could not validate the certificates chain.",
            extra=dict(error=str(exc), leaf_certificate_x509=leaf_certificate_x509, other_certificates_bytes=other_certificates_bytes),
        )
        raise SafetyNetVerificationError()


def _verify_signature(jws_token: str, leaf_certificate: crypto.x509) -> None:
    """
    Verify that the jws_token has been signed with the public key specified in the header.

    :param jws_token: the jws token to validate.
    :param leaf_certificate: the leaf certificate extracted from the jws header.
    """
    public_key = crypto.dump_publickey(crypto.FILETYPE_PEM, leaf_certificate.get_pubkey())
    try:
        jwt.decode(jws_token, public_key)
    except DecodeError as exc:
        _LOGGER.warning(
            "Could not verify jws signature.",
            extra=dict(error=str(exc), jws_token=jws_token, public_key=public_key),
        )
        raise SafetyNetVerificationError()


def _generate_nonce(operational_info: OperationalInfo, salt: str) -> str:
    """
    Generate the payload nonce from the operational information and the salt.
    This digest must be the same specified in the client implementation.

    :param operational_info: the operational information related to the SafetyNet payload.
    :param salt: the salt used in the SafetyNet payload.
    :return: a SHA256 encode hash representing the nonce.
    """
    nonce = (
        f"{operational_info.province}"
        f"{int(operational_info.exposure_permission)}"
        f"{int(operational_info.bluetooth_active)}"
        f"{int(operational_info.notification_permission)}"
        f"{int(operational_info.exposure_notification)}"
        f"{operational_info.last_risky_exposure_on}"
        f"{salt}"
    )

    return sha256(nonce.encode("utf-8")).hexdigest()


def _validate_payload(
    payload: Dict[str, Any], operational_info: OperationalInfo, salt: str
) -> None:
    """
    Validate the jws payload.

    :param payload: the jws decoded payload.
    :param operational_info: the device operational information.
    :param salt: the salt sent in the request.
    :raises: SafetyNetVerificationError.
    """
    lower_bound_skew = (
        datetime.utcnow() - timedelta(minutes=config.SAFETY_NET_MAX_SKEW_MINUTES)
    ).timestamp() * 1000
    upper_bound_skew = (
        datetime.utcnow() + timedelta(minutes=config.SAFETY_NET_MAX_SKEW_MINUTES)
    ).timestamp() * 1000

    # TODO apkCertificateDigestSha256
    if not (
        lower_bound_skew <= payload["timestampMs"] <= upper_bound_skew
        and payload["nonce"] == _generate_nonce(operational_info, salt)
        and payload["apkPackageName"] == _PACKAGE_NAME
        and payload["basicIntegrity"] is True
        and payload["ctsProfileMatch"] is True
        and "HARDWARE_BACKED" in payload["evaluationType"].split(",")
    ):
        _LOGGER.warning(
            "The jws payload did not pass the validation check.",
            extra=dict(
                payload=payload,
                lower_bound_skew=lower_bound_skew,
                upper_bound_skew=upper_bound_skew,
            ),
        )
        raise SafetyNetVerificationError()


def verify_attestation(
    safety_net_attestation: str, salt: str, operational_info: OperationalInfo
) -> None:
    """
    Verify that the safety_net_payload is valid, signed by Google and formatted as expected.

    :param safety_net_attestation: the SafetyNet attestation to validate.
    :param salt: the salt sent in the request.
    :param operational_info: the device operational information.
    :raises: SafetyNetVerificationError.
    """
    header = _get_jws_header(safety_net_attestation)
    certificates = _get_certificates(header)
    leaf_certificate = _get_leaf_certificate_x509(certificates[0])
    _validate_certificates(leaf_certificate, other_certificates_bytes=certificates[1:])
    _verify_signature(safety_net_attestation, leaf_certificate)
    payload = _get_jws_payload(safety_net_attestation)
    _validate_payload(payload, operational_info, salt)
