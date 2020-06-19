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
import json
from datetime import date, datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from freezegun import freeze_time
from pytest import mark, raises

from immuni_analytics.core import config
from immuni_analytics.helpers.safety_net import (
    MalformedJwsToken,
    SafetyNetVerificationError,
    _get_certificates,
    _get_jws_header,
    _get_jws_part,
    _get_jws_payload,
    _load_leaf_certificate,
    _parse_jws_part,
    _validate_certificates,
    _verify_signature,
    get_redis_key,
    verify_attestation,
)
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform
from tests.fixtures.safety_net import POST_TIMESTAMP, TEST_APK_DIGEST

_JWS_EXAMPLE = (
    "eyJ0eXAiOiJKV1QiLA0KICJhbGciOiJIUzI1NiJ9."
    "eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19y"
    "b290Ijp0cnVlfQ."
    "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
)


def test_get_redis_key() -> None:
    assert "~safetynet-used-salt:my-salt" == get_redis_key("my-salt")


def test_get_jws_part() -> None:
    # A jws token is a string composed of three sub-strings divided by dots.
    fake_jws = "first.second.third"
    assert _get_jws_part(fake_jws, 0) == "first"
    assert _get_jws_part(fake_jws, 1) == "second"
    assert _get_jws_part(fake_jws, 2) == "third"


@mark.parametrize("wrong_jws", ["first.second", "first.second.third.fourth.fifth", ""])
def test_get_jws_part_raises_if_wrong_parts(wrong_jws: str) -> None:
    with raises(MalformedJwsToken):
        _get_jws_part(wrong_jws, 1)


def test_parse_jws_part() -> None:
    test_dict = {"test": "val", "test1": 1, "test2": {"a": 1, "ba": True}}
    base64encoded = base64.b64encode(json.dumps(test_dict).encode()).decode()
    # remove padding
    base64encoded = base64encoded.rstrip("=")

    assert _parse_jws_part(base64encoded) == test_dict


def test_get_jws_header() -> None:
    assert _get_jws_header(_JWS_EXAMPLE) == {"typ": "JWT", "alg": "HS256"}


def test_get_jws_payload() -> None:
    assert _get_jws_payload(_JWS_EXAMPLE) == {
        "iss": "joe",
        "exp": 1300819380,
        "http://example.com/is_root": True,
    }


@mark.parametrize(
    "wrong_jws",
    [
        f"{_JWS_EXAMPLE}.fourth",
        ".".join(_JWS_EXAMPLE.split(".")[:2]),
        f"{_JWS_EXAMPLE[:3]}{_JWS_EXAMPLE[4:]}",
    ],
)
@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_get_jws_header_raises(warning_logger: MagicMock, wrong_jws: str) -> None:
    with raises(SafetyNetVerificationError):
        _get_jws_header(wrong_jws)

    warning_logger.assert_called_once()


@mark.parametrize(
    "wrong_jws",
    [
        f"{_JWS_EXAMPLE}.fourth",
        ".".join(_JWS_EXAMPLE.split(".")[:2]),
        f"{_JWS_EXAMPLE[:40]}{_JWS_EXAMPLE[42:]}",
    ],
)
@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_get_jws_payload_raises(warning_logger: MagicMock, wrong_jws: str) -> None:
    with raises(SafetyNetVerificationError):
        _get_jws_payload(wrong_jws)

    warning_logger.assert_called_once()


def _operational_info_from_post_body(post_body: Dict[str, Any]) -> OperationalInfo:
    return OperationalInfo(
        platform=Platform.ANDROID,
        province=post_body["province"],
        exposure_permission=post_body["exposure_permission"],
        bluetooth_active=post_body["bluetooth_active"],
        notification_permission=post_body["notification_permission"],
        exposure_notification=post_body["exposure_notification"],
        last_risky_exposure_on=None
        if not post_body["exposure_notification"]
        else date.fromisoformat(post_body["last_risky_exposure_on"]),
    )


@freeze_time(datetime.utcfromtimestamp(POST_TIMESTAMP))
def test_verify(safety_net_post_body_with_exposure: Dict[str, Any]) -> None:
    operational_info = _operational_info_from_post_body(safety_net_post_body_with_exposure)
    with patch("immuni_analytics.helpers.safety_net.config.SAFETY_NET_APK_DIGEST", TEST_APK_DIGEST):
        verify_attestation(
            safety_net_post_body_with_exposure["signed_attestation"],
            safety_net_post_body_with_exposure["salt"],
            operational_info,
            safety_net_post_body_with_exposure["last_risky_exposure_on"],
        )


@freeze_time(
    datetime.utcfromtimestamp(POST_TIMESTAMP)
    - timedelta(minutes=config.SAFETY_NET_MAX_SKEW_MINUTES + 1)
)
@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_verify_raises_if_too_skewed(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    operational_info = _operational_info_from_post_body(safety_net_post_body_with_exposure)
    with raises(SafetyNetVerificationError):
        verify_attestation(
            safety_net_post_body_with_exposure["signed_attestation"],
            safety_net_post_body_with_exposure["salt"],
            operational_info,
            safety_net_post_body_with_exposure["last_risky_exposure_on"],
        )

    warning_logger.assert_called_once()


@freeze_time(
    datetime.utcfromtimestamp(POST_TIMESTAMP)
    - timedelta(minutes=config.SAFETY_NET_MAX_SKEW_MINUTES + 1)
)
@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_verify_raises_if_nonce_changes(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    safety_net_post_body_with_exposure["salt"] = "random_string"
    operational_info = _operational_info_from_post_body(safety_net_post_body_with_exposure)
    with raises(SafetyNetVerificationError):
        verify_attestation(
            safety_net_post_body_with_exposure["signed_attestation"],
            safety_net_post_body_with_exposure["salt"],
            operational_info,
            safety_net_post_body_with_exposure["last_risky_exposure_on"],
        )

    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_get_certificate_raises_if_missing_key(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    header = _get_jws_header(safety_net_post_body_with_exposure["signed_attestation"])
    header.pop("x5c")

    with raises(SafetyNetVerificationError):
        _get_certificates(header)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_get_certificate_raises_if_wrong_encoding(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    header = _get_jws_header(safety_net_post_body_with_exposure["signed_attestation"])
    header["x5c"][0] = "non_base64_string"
    with raises(SafetyNetVerificationError):
        _get_certificates(header)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_validate_certificate_raises_if_wrong_path(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    header = _get_jws_header(safety_net_post_body_with_exposure["signed_attestation"])
    certificates = _get_certificates(header)
    certificates.reverse()

    with raises(SafetyNetVerificationError):
        _validate_certificates(certificates)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_validate_certificate_raises_if_wrong_issuer(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    header = _get_jws_header(safety_net_post_body_with_exposure["signed_attestation"])
    certificates = _get_certificates(header)
    with patch(
        "immuni_analytics.helpers.safety_net.config.SAFETY_NET_ISSUER_HOSTNAME", "wrong.issuer.com"
    ):
        with raises(SafetyNetVerificationError):
            _validate_certificates(certificates)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_raises_if_invalid_leaf(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    header = _get_jws_header(safety_net_post_body_with_exposure["signed_attestation"])
    certificates = _get_certificates(header)
    certificates[0] = certificates[0][:20] + certificates[0][22:]
    with raises(SafetyNetVerificationError):
        _load_leaf_certificate(certificates)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_verify_signature_raises_if_wrong_leaf(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    attestation = safety_net_post_body_with_exposure["signed_attestation"]
    header = _get_jws_header(attestation)
    certificates = _get_certificates(header)
    certificates.reverse()
    with raises(SafetyNetVerificationError):
        _verify_signature(attestation, certificates)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_verify_signature_raises_if_wrong_signature(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    attestation = safety_net_post_body_with_exposure["signed_attestation"]
    header = _get_jws_header(attestation)
    certificates = _get_certificates(header)

    wrong_attestation_signature = ".".join(
        attestation.split(".")[:2] + [_JWS_EXAMPLE.split(".")[2]]
    )
    with raises(SafetyNetVerificationError):
        _verify_signature(wrong_attestation_signature, certificates)
    warning_logger.assert_called_once()


@patch("immuni_analytics.helpers.safety_net._LOGGER.warning")
def test_verify_signature_raises_if_wrong_public_key_format(
    warning_logger: MagicMock, safety_net_post_body_with_exposure: Dict[str, Any]
) -> None:
    attestation = safety_net_post_body_with_exposure["signed_attestation"]
    header = _get_jws_header(attestation)
    certificates = _get_certificates(header)

    with patch(
        "immuni_analytics.helpers.safety_net._load_leaf_certificate",
        return_value=MagicMock(**{"public_key.return_value": "unexpected_type"}),
    ):
        with raises(SafetyNetVerificationError):
            _verify_signature(attestation, certificates)

    warning_logger.assert_called_once_with(
        "Unexpected certificate public_key type.", extra=dict(public_key="unexpected_type")
    )
