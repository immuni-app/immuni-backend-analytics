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

import logging
from datetime import date
from http import HTTPStatus
from typing import Any

from marshmallow import fields
from marshmallow.validate import Length
from sanic import Blueprint
from sanic.request import Request
from sanic.response import HTTPResponse
from sanic_openapi import doc

from immuni_analytics.celery.authorization_android.tasks.verify_safety_net_attestation import (
    verify_safety_net_attestation,
)
from immuni_analytics.celery.authorization_ios.tasks.authorize_analytics_token import (
    authorize_analytics_token,
)
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers import safety_net
from immuni_analytics.helpers.api import inject_operational_info
from immuni_analytics.helpers.redis import (
    enqueue_operational_info,
    get_upload_authorization_member_for_current_month,
    is_upload_authorized_for_token,
)
from immuni_analytics.models.marshmallow import AnalyticsToken, validate_analytics_token_from_bearer
from immuni_analytics.models.operational_info import OperationalInfo as OperationalInfoDocument
from immuni_analytics.models.swagger import (
    AppleOperationalInfo,
    AuthorizationBody,
    GoogleOperationalInfo,
)
from immuni_analytics.monitoring.api import OPERATIONAL_INFO_ANDROID_REUSED_SALT
from immuni_analytics.monitoring.helpers import monitor_operational_info
from immuni_common.core.exceptions import SchemaValidationException
from immuni_common.helpers.sanic import handle_dummy_requests, json_response, validate
from immuni_common.helpers.swagger import doc_exception
from immuni_common.helpers.utils import WeightedPayload
from immuni_common.models.enums import Location, Platform
from immuni_common.models.marshmallow.fields import (
    Base64String,
    IntegerBoolField,
    IsoDate,
    Province,
)
from immuni_common.models.swagger import HeaderImmuniContentTypeJson

_LOGGER = logging.getLogger(__name__)

bp = Blueprint("analytics", url_prefix="analytics")


@bp.route("/apple/operational-info", methods=["POST"], version=1)
@doc.summary("Upload iOS operational info (caller: Mobile Client.)")
@doc.description(
    "Save the operational data sent by the iOS device, in compliance with the monthly policy,"
    " authorized with the provided analytics token."
)
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc.consumes(
    doc.String(name="Authorization", description="Bearer <analytics_token>"),
    location="header",
    required=True,
)
@doc.consumes(
    AppleOperationalInfo,
    content_type="application/json; charset=utf-8",
    location="body",
    required=True,
)
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.NO_CONTENT.value, None, description="Operation completed successfully.",
)
@validate(
    location=Location.JSON,
    bluetooth_active=IntegerBoolField(required=True),
    exposure_notification=IntegerBoolField(required=True),
    exposure_permission=IntegerBoolField(required=True),
    notification_permission=IntegerBoolField(required=True),
    last_risky_exposure_on=IsoDate(),
    province=Province(),
)
@monitor_operational_info
# Dummy requests are currently being filtered at the reverse proxy level, emulating the same
# behavior implemented below and introducing a response delay.
# This may be re-evaluated in the future.
@handle_dummy_requests(
    [WeightedPayload(weight=1, payload=json_response(body=None, status=HTTPStatus.NO_CONTENT))]
)
@inject_operational_info(platform=Platform.IOS)
async def post_apple_operational_info(
    request: Request, operational_info: OperationalInfoDocument, **kwargs: Any
) -> HTTPResponse:
    """
    Check if the analytics_token is authorized and save the operational data in compliance with the
    rate limiting policy.

    :param request: the HTTP request object.
    :param operational_info: the operational information to save.
    :return: 204 in any case.
    """
    analytics_token = validate_analytics_token_from_bearer(request.token)
    if await managers.authorization_ios_redis.srem(
        analytics_token,
        get_upload_authorization_member_for_current_month(operational_info.exposure_notification),
    ):
        await enqueue_operational_info(operational_info)

    return json_response(body=None, status=HTTPStatus.NO_CONTENT)


@bp.route("/google/operational-info", methods=["POST"], version=1)
@doc.summary("Upload android operational info (caller: Mobile Client.)")
@doc.description(
    "Save the operational data sent by the Android device, authorized with the provided"
    " SafetyNet hardware attestation token."
)
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc.consumes(
    GoogleOperationalInfo,
    content_type="application/json; charset=utf-8",
    location="body",
    required=True,
)
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.NO_CONTENT.value, None, description="Operation completed successfully.",
)
@validate(
    location=Location.JSON,
    bluetooth_active=IntegerBoolField(required=True),
    exposure_notification=IntegerBoolField(required=True),
    exposure_permission=IntegerBoolField(required=True),
    notification_permission=IntegerBoolField(required=True),
    last_risky_exposure_on=IsoDate(),
    province=Province(),
    salt=Base64String(
        required=True, min_encoded_length=config.SALT_LENGTH, max_encoded_length=config.SALT_LENGTH
    ),
    signed_attestation=fields.String(
        required=True, validate=Length(max=config.SIGNED_ATTESTATION_MAX_LENGTH)
    ),
)
@monitor_operational_info
# Dummy requests are currently being filtered at the reverse proxy level, emulating the same
# behavior implemented below and introducing a response delay.
# This may be re-evaluated in the future.
@handle_dummy_requests(
    [WeightedPayload(weight=1, payload=json_response(body=None, status=HTTPStatus.NO_CONTENT))]
)
@inject_operational_info(platform=Platform.ANDROID)
async def post_android_operational_info(
    request: Request,
    last_risky_exposure_on: date,
    operational_info: OperationalInfoDocument,
    salt: str,
    signed_attestation: str,
    **kwargs: Any,
) -> HTTPResponse:
    """
    Check if the signed attestation is valid and the salt has not recently been used.
    In case of success save the operational_info.

    :param request: the HTTP request object.
    :param last_risky_exposure_on: the date on which the last Risky Exposure took place, if any.
    :param operational_info: the operational information to save.
    :param salt: a random string sent by the client to prevent replay attacks.
    :param signed_attestation: the payload generated by Google SafetyNet attestation API.
    :return: 204 in any case.
    """
    if await managers.authorization_android_redis.get(safety_net.get_redis_key(salt)):
        _LOGGER.warning(
            "Found previously used salt.",
            extra=dict(signed_attestation=signed_attestation, salt=salt),
        )
        OPERATIONAL_INFO_ANDROID_REUSED_SALT.labels(False).inc()
        return json_response(body=None, status=HTTPStatus.NO_CONTENT)

    verify_safety_net_attestation.delay(
        signed_attestation, salt, operational_info.to_dict(), last_risky_exposure_on.isoformat(),
    )

    return json_response(body=None, status=HTTPStatus.NO_CONTENT)


@bp.route("/apple/token", methods=["POST"], version=1)
@doc.summary("Authorize an analytics_token (caller: Mobile Client.)")
@doc.description(
    "Authorize the provided analytics token with the device authenticity SDK offered by the"
    " device operating system."
)
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc.consumes(
    AuthorizationBody,
    content_type="application/json; charset=utf-8",
    location="body",
    required=True,
)
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.CREATED.value, None, description="Token is authorized.",
)
@doc.response(
    HTTPStatus.ACCEPTED.value, None, description="Token authorization in progress.",
)
@validate(
    location=Location.JSON,
    analytics_token=AnalyticsToken(),
    device_token=Base64String(required=True, max_encoded_length=config.DEVICE_TOKEN_MAX_LENGTH),
)
async def authorize_token(
    request: Request, analytics_token: str, device_token: str
) -> HTTPResponse:
    """
    Check if the device_token is genuine and, if so, authorize the analytics_token.

    :param request: the HTTP request.
    :param analytics_token: the analytics_token to authorize for the operational_info uploads.
    :param device_token: the device token to check against Apple DeviceCheck.
    :return: 201 if the token has been authorized already, 202 otherwise.
    """
    if await is_upload_authorized_for_token(analytics_token):
        return json_response(body=None, status=HTTPStatus.CREATED)

    authorize_analytics_token.delay(analytics_token, device_token)

    return json_response(body=None, status=HTTPStatus.ACCEPTED)
