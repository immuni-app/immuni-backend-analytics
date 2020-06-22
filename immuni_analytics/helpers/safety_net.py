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

import base64
import binascii
import json
import logging
from datetime import datetime, timedelta
from hashlib import sha256
from json import JSONDecodeError
from typing import Any, Dict, List, NamedTuple

import certvalidator
import jwt
from certvalidator import CertificateValidator
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.x509 import Certificate, load_der_x509_certificate
from jwt import DecodeError

from immuni_analytics.core import config
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.core.exceptions import ImmuniException

_LOGGER = logging.getLogger(__name__)


class SafetyNetVerificationError(ImmuniException):
    """
    Raised when one of the steps in the verification fails.
    """


class MalformedJwsToken(ImmuniException):
    """
    Raised when the JSW token is malformed.
    """

    def __init__(self, jws_token: str) -> None:
        super().__init__(f"Malformed JWS token: {jws_token}.")


class DecodedJWS(NamedTuple):
    """
    Named tuple to access the decoded jws token.
    """

    header: Dict[str, Any]
    payload: Dict[str, Any]
    signature: str


def get_redis_key(salt: str) -> str:
    """
    Retrieve the redis key for a given salt.

    :param salt: the salt corresponding to a request.
    :return: the redis key containing the salt.
    """
    return f"~safetynet-used-salt:{salt}"


def _decode_jws(jws_token: str) -> DecodedJWS:
    """
    Split the jws token in its different parts and decode them.

    :param jws_token: the jws_token to split.
    :return: the jws_token part specified by index.
    :raises: MalformedJwsToken if the token cannot be decoded.
    """

    if len(parts := jws_token.split(".")) == 3:
        try:
            return DecodedJWS(
                header=_parse_jws_part(parts[0]),
                payload=_parse_jws_part(parts[1]),
                signature=parts[2],
            )
        except (binascii.Error, JSONDecodeError, UnicodeDecodeError,) as exc:
            _LOGGER.warning(
                "Could not decode jws token.", extra=dict(error=str(exc), jws_token=jws_token),
            )
            raise MalformedJwsToken(jws_token)

    _LOGGER.warning(
        "Could not decode jws token. Unexpected number of parts.",
        extra=dict(jws_token=jws_token, jws_parts=parts),
    )
    raise MalformedJwsToken(jws_token)


def _parse_jws_part(jws_part: str) -> Dict[str, Any]:
    """
    Parse a base64 jsw part, adding padding if necessary, into a dictionary.

    :param jws_part: the base string to b64decode.
    :return: the decoded string.
    :raises: binascii.Error if the base64decode fails.
     JSONDecodeError if the json decode fails.
     UnicodeDecodeError if the decode from binary fails.
    """
    padding = "=" * (4 - (len(jws_part) % 4))
    padded_jws_part = f"{jws_part}{padding}"

    return json.loads(base64.b64decode(padded_jws_part).decode())


def _get_certificates(header: Dict[str, Any]) -> List[bytes]:
    """
    Retrieve the certificates from the jws header.

    :param header: the jws header.
    :return: the list of retrieved certificates.
    :raises: SafetyNetVerificationError if the certificates could not be retrieved or decoded.
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


def _load_leaf_certificate(certificates: List[bytes]) -> Certificate:
    """
    Load the lead certificate give the list of certificates.

    :param certificates: the list of certificates.
    :return: the loaded leaf certificate.
    :raises: SafetyNetVerificationError if the leaf certificate could not be loaded.
    """
    leaf_certificate = certificates[0]
    try:
        return load_der_x509_certificate(leaf_certificate, default_backend())
    except (ValueError, UnsupportedAlgorithm) as exc:
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
    :raises: SafetyNetVerificationError if the certificate chain is not valid or the hostname is
     not the expected one.
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
    public_key = leaf_certificate.public_key()
    if not isinstance(public_key, RSAPublicKey):
        _LOGGER.warning(
            "Unexpected certificate public_key type.", extra=dict(public_key=public_key),
        )
        raise SafetyNetVerificationError()
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


# pylint: disable=duplicate-code
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
    decoded_jws = _decode_jws(safety_net_attestation)
    certificates = _get_certificates(decoded_jws.header)
    _validate_certificates(certificates)
    _verify_signature(safety_net_attestation, certificates)
    _validate_payload(decoded_jws.payload, operational_info, salt, last_risky_exposure_on)
