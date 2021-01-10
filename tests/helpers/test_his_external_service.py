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

from hashlib import sha256

from immuni_analytics.helpers.his_external_service import invalidate_cun
from immuni_common.core.exceptions import (
    ApiException,
    OtpCollisionException,
    SchemaValidationException,
    UnauthorizedOtpException,
)
from tests.fixtures.core import config_set
from tests.fixtures.his_external_service import (
    mock_external_his_service_api_exception,
    mock_external_his_service_otp_collision,
    mock_external_his_service_schema_validation,
    mock_external_his_service_unauthorized_otp,
)


def test_his_external_service_schema_validation() -> None:
    with config_set(
        "HIS_INVALIDATE_EXTERNAL_URL", "example.com"
    ), mock_external_his_service_schema_validation():
        try:
            invalidate_cun(
                cun_sha="b39e0733843b1b5d7",
                id_test_verification="2d8af3b9-2c0a-4efc-9e15-72454f994e1f",
            )
        except SchemaValidationException as e:
            assert e


def test_his_external_service_unauthorized_otp() -> None:
    with config_set(
        "HIS_INVALIDATE_EXTERNAL_URL", "example.com"
    ), mock_external_his_service_unauthorized_otp():
        try:
            invalidate_cun(
                cun_sha=sha256("59FU36KR46".encode("utf-8")).hexdigest(),
                id_test_verification="2d8af3b9-2c0a-4efc-9e15-72454f994e1f",
            )
        except UnauthorizedOtpException as e:
            assert e


def test_his_external_service_otp_collision() -> None:
    with config_set(
        "HIS_INVALIDATE_EXTERNAL_URL", "example.com"
    ), mock_external_his_service_otp_collision():
        try:
            invalidate_cun(
                cun_sha=sha256("59FU36KR46".encode("utf-8")).hexdigest(),
                id_test_verification="2d8af3b9-2c0a-4efc-9e15-72454f994e1f",
            )
        except OtpCollisionException as e:
            assert e


def test_his_external_service_api_exception() -> None:
    with config_set(
        "HIS_INVALIDATE_EXTERNAL_URL", "example.com"
    ), mock_external_his_service_api_exception():
        try:
            invalidate_cun(
                cun_sha=sha256("59FU36KR46".encode("utf-8")).hexdigest(),
                id_test_verification="2d8af3b9-2c0a-4efc-9e15-72454f994e1f",
            )
        except ApiException as e:
            assert e
