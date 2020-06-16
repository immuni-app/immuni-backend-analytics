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

    raise ValueError("The jws token is badly formatted")


def _parse_jws_part(jws_part: str) -> Dict[str, Any]:
    """
    Parse a base64 jsw part, adding padding if necessary, into a dictionary.

    :param jws_part: the base string to b64decode.
    :return: the decoded string.
    """
    padding = "=" * (4 - (len(jws_part) % 4))
    padded_jws_part = f"{jws_part}{padding}"

    return json.loads(base64.b64decode(padded_jws_part).decode())


def _get_jws_header(jws_token: str) -> Dict[str, Any]:
    """
    Retrieve the header of a jws token.

    :param jws_token: the jws token to get the header from.
    :return: the jws token header.
    :raises: SafetyNetVerificationError if the header could not be retrieved.
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
    :raises: SafetyNetVerificationError if the payload could not be retrieved.
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
    """
    Retrieve the certificates from the jws header.

    :param header: the jws header.
    :raises: SafetyNetVerificationError if the certificates could not be retrieved or decoded.
    "
    """
    try:
        certificates_string = header["x5c"]
    except KeyError:
        _LOGGER.warning(
            "Could not retrieve certificates from the jws header.", extra=dict(header=header),
        )
        raise SafetyNetVerificationError()

    try:
        certificates = [base64.b64decode(c) for c in certificates_string]
    except binascii.Error as exc:
        _LOGGER.warning(
            "Could not decode the jws header certificates.",
            extra=dict(error=str(exc), certificates_string=certificates_string),
        )
        raise SafetyNetVerificationError()

    return certificates


def _load_leaf_certificate(certificates: List[bytes]) -> crypto.x509:
    """
    Load the lead certificate give the list of certificates.

    :param certificates: the list of certificates.
    :return: the loaded leaf certificate.
    :raises: SafetyNetVerificationError if the leaf certificate could not be loaded.
    """
    leaf_certificate = certificates[0]
    try:
        return crypto.load_certificate(crypto.FILETYPE_ASN1, leaf_certificate)
    except crypto.Error as exc:
        _LOGGER.warning(
            "Could not load the leaf certificate.",
            extra=dict(error=str(exc), leaf_certificate=leaf_certificate),
        )
        raise SafetyNetVerificationError()


def _validate_certificates(certificates: List[bytes]) -> None:
    """
    Validate the SSL certificate chain and use SSL hostname matching to verify that the leaf
    certificate was issued to the _ISSUER_HOSTNAME.

    :param certificates: the list of certificates.
    :return: the leaf certificate.
    """
    try:
        validator = CertificateValidator(certificates[0], certificates[1:])
        validator.validate_tls(config.SAFETY_NET_ISSUER_HOSTNAME)
    except certvalidator.errors.ValidationError as exc:
        _LOGGER.warning(
            "Could not validate the certificates chain.",
            extra=dict(error=str(exc), certificates=certificates,),
        )
        raise SafetyNetVerificationError()


def _verify_signature(jws_token: str, certificates: List[bytes]) -> None:
    """
    Verify that the jws_token has been signed with the public key specified in the header.

    :param jws_token: the jws token to validate.
    :param certificates: the list of certificates.
    :raises: SafetyNetVerificationError if the signature could not be verified.
    """
    leaf_certificate = _load_leaf_certificate(certificates)
    public_key = crypto.dump_publickey(crypto.FILETYPE_PEM, leaf_certificate.get_pubkey())
    try:
        jwt.decode(jws_token, public_key)
    except DecodeError as exc:
        _LOGGER.warning(
            "Could not verify jws signature.",
            extra=dict(error=str(exc), jws_token=jws_token, public_key=public_key),
        )
        raise SafetyNetVerificationError()


def _generate_nonce(
    operational_info: OperationalInfo, salt: str, last_risky_exposure_on: str
) -> str:
    """
    Generate the payload nonce from the operational information and the salt.
    This digest must be the same specified in the client implementation.

    :param operational_info: the operational information related to the SafetyNet payload.
    :param salt: the salt used in the SafetyNet payload.
    :param last_risky_exposure_on: the last risky exposure isoformat date.
    :return: a base64 encoded SHA256 digest representing the nonce.
    """
    nonce = (
        f"{operational_info.province}"
        f"{int(operational_info.exposure_permission)}"
        f"{int(operational_info.bluetooth_active)}"
        f"{int(operational_info.notification_permission)}"
        f"{int(operational_info.exposure_notification)}"
        f"{last_risky_exposure_on}"
        f"{salt}"
    )

    return base64.b64encode(sha256(nonce.encode("utf-8")).digest()).decode("utf-8")


def _validate_payload(
    payload: Dict[str, Any],
    operational_info: OperationalInfo,
    salt: str,
    last_risky_exposure_on: str,
) -> None:
    """
    Validate the jws payload.

    :param payload: the jws decoded payload.
    :param operational_info: the device operational information.
    :param salt: the salt sent in the request.
    :param last_risky_exposure_on: the last risky exposure isoformat date.
    :raises: SafetyNetVerificationError if at least one requirement is not met.
    """
    lower_bound_skew = (
        datetime.utcnow() - timedelta(minutes=config.SAFETY_NET_MAX_SKEW_MINUTES)
    ).timestamp() * 1000
    upper_bound_skew = (
        datetime.utcnow() + timedelta(minutes=config.SAFETY_NET_MAX_SKEW_MINUTES)
    ).timestamp() * 1000

    if not (
        lower_bound_skew <= payload["timestampMs"] <= upper_bound_skew
        and payload["nonce"] == _generate_nonce(operational_info, salt, last_risky_exposure_on)
        and payload["apkPackageName"] == config.SAFETY_NET_PACKAGE_NAME
        and payload["apkCertificateDigestSha256"][0] == config.SAFETY_NET_APK_DIGEST
        and payload["basicIntegrity"] is True
        and payload["ctsProfileMatch"] is True
        and "HARDWARE_BACKED" in payload["evaluationType"].split(",")
    ):
        _LOGGER.warning(
            "The jws payload did not pass the validation check.",
            extra=dict(
                payload=payload,
                salt=salt,
                lower_bound_skew=lower_bound_skew,
                upper_bound_skew=upper_bound_skew,
                generated_nonce=_generate_nonce(operational_info, salt, last_risky_exposure_on),
            ),
        )
        raise SafetyNetVerificationError()


def verify_attestation(
    safety_net_attestation: str,
    salt: str,
    operational_info: OperationalInfo,
    last_risky_exposure_on: str,
) -> None:
    """
    Verify that the safety_net_payload is valid, signed by Google and formatted as expected.

    :param safety_net_attestation: the SafetyNet attestation to validate.
    :param salt: the salt sent in the request.
    :param operational_info: the device operational information.
    :param last_risky_exposure_on: the last risky exposure isoformat date.
    :raises: SafetyNetVerificationError if any of the retrieval or validation steps fail.
    """
    header = _get_jws_header(safety_net_attestation)
    certificates = _get_certificates(header)
    _validate_certificates(certificates)
    _verify_signature(safety_net_attestation, certificates)
    payload = _get_jws_payload(safety_net_attestation)
    _validate_payload(payload, operational_info, salt, last_risky_exposure_on)
