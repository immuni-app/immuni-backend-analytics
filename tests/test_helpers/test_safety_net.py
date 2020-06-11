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
import json
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from freezegun import freeze_time
from pytest import mark, raises

from immuni_analytics.helpers.safety_net import (
    SafetyNetVerificationError,
    _get_jws_header,
    _get_jws_part,
    _get_jws_payload,
    _parse_jws_part,
    get_redis_key,
    verify_attestation,
)
from immuni_analytics.models.operational_info import OperationalInfo
from immuni_common.models.enums import Platform

from tests.fixtures.safety_net import POST_TIMESTAMP

_JWS_EXAMPLE = (
    "eyJ0eXAiOiJKV1QiLA0KICJhbGciOiJIUzI1NiJ9."
    "eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19y"
    "b290Ijp0cnVlfQ."
    "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
)


def test_get_redis_key() -> None:
    assert f"~safetynet-used-salt:my-salt" == get_redis_key("my-salt")


def test_get_jws_part() -> None:
    # A jws token is a string composed of three sub-strings divided by dots.
    fake_jws = "first.second.third"
    assert _get_jws_part(fake_jws, 0) == "first"
    assert _get_jws_part(fake_jws, 1) == "second"
    assert _get_jws_part(fake_jws, 2) == "third"


@mark.parametrize("wrong_jws", ["first.second", "first.second.third.fourth.fifth", ""])
def test_get_jws_part_raises_if_wrong_parts(wrong_jws: str) -> None:
    with raises(ValueError):
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


@freeze_time(datetime.utcfromtimestamp(POST_TIMESTAMP))
def test_verify(safety_net_post_body: Dict[str, Any]) -> None:
    operational_info = OperationalInfo(
        platform=Platform.ANDROID,
        province=safety_net_post_body["province"],
        exposure_permission=safety_net_post_body["exposure_permission"],
        bluetooth_active=safety_net_post_body["bluetooth_active"],
        notification_permission=safety_net_post_body["notification_permission"],
        exposure_notification=safety_net_post_body["exposure_notification"],
        last_risky_exposure_on=safety_net_post_body["last_risky_exposure_on"],
    )
    verify_attestation(safety_net_post_body["signed_attestation"], safety_net_post_body["salt"], operational_info)
