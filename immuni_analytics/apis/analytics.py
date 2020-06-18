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

import logging
from datetime import date
from http import HTTPStatus
from typing import Any

from marshmallow import fields
from marshmallow.validate import Length, Regexp
from sanic import Blueprint
from sanic.request import Request
from sanic.response import HTTPResponse
from sanic_openapi import doc

from immuni_analytics.celery.authorization.tasks.authorize_analytics_token import (
    authorize_analytics_token,
)
from immuni_analytics.celery.authorization.tasks.verify_safety_net_attestation import (
    verify_safety_net_attestation,
)
from immuni_analytics.core import config
from immuni_analytics.core.managers import managers
from immuni_analytics.helpers import safety_net
from immuni_analytics.helpers.api import allows_dummy_requests, inject_operational_info
from immuni_analytics.helpers.redis import (
    enqueue_operational_info,
    get_upload_authorization_member_for_current_month,
    is_upload_authorized_for_token,
)
from immuni_analytics.models.operational_info import OperationalInfo as OperationalInfoDocument
from immuni_analytics.models.swagger import (
    AppleOperationalInfo,
    AuthorizationBody,
    GoogleOperationalInfo,
)
from immuni_common.core.exceptions import SchemaValidationException
from immuni_common.helpers.sanic import json_response, validate
from immuni_common.helpers.swagger import doc_exception
from immuni_common.models.enums import Location
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
@doc.summary("Upload operational info (caller: Mobile Client.)")
@doc.description(
    "Check if the analytics_token is authorized to upload and save the operational info"
    " in the database."
)
@doc.consumes(AppleOperationalInfo, location="body")
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc.consumes(
    doc.String(name="Authorization", description="Bearer <ANALYTICS_TOKEN>"),
    location="header",
    required=True,
)
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.NO_CONTENT.value, None, description="Well-formed request.",
)
@validate(
    location=Location.JSON,
    province=Province(),
    exposure_permission=IntegerBoolField(required=True),
    bluetooth_active=IntegerBoolField(required=True),
    notification_permission=IntegerBoolField(required=True),
    exposure_notification=IntegerBoolField(required=True),
    last_risky_exposure_on=IsoDate(),
)
@allows_dummy_requests
@inject_operational_info
async def post_operational_info(
    request: Request, operational_info: OperationalInfoDocument, **kwargs: Any
) -> HTTPResponse:
    """
    Check if the analytics_token is authorized and save the operational data
    in compliance with the rate limiting policy.

    :param request: the HTTP request object.
    :param operational_info: The operational information to be saved.
    :return: 204 in any case.
    """
    if await managers.analytics_redis.srem(
        request.token,
        get_upload_authorization_member_for_current_month(operational_info.exposure_notification),
    ):
        await enqueue_operational_info(operational_info)

    return json_response(body=None, status=HTTPStatus.NO_CONTENT)


@bp.route("/apple/token", methods=["POST"], version=1)
@doc.summary("Authorize an analytics_token (caller: Mobile Client.)")
@doc.description(
    "Check if the device_token is genuine and allow the analytics_token to be used as"
    " an authorization token in compliance with the rate limiting policy."
)
@doc.consumes(AuthorizationBody, location="body")
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.NO_CONTENT.value, None, description="Well-formed request.",
)
@validate(
    location=Location.JSON,
    analytics_token=fields.String(
        required=True, validate=Regexp(rf"^[a-f0-9]{{{config.ANALYTICS_TOKEN_SIZE}}}$")
    ),
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


@bp.route("/google/operational-info", methods=["POST"], version=1)
@doc.summary("Upload android operational info (caller: Mobile Client.)")
@doc.description(
    "Check if the signed attestation is genuine and save the operational information in "
    "the database."
)
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc.consumes(GoogleOperationalInfo, location="body")
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.NO_CONTENT.value, None, description="Well-formed request.",
)
@validate(
    location=Location.JSON,
    province=Province(),
    exposure_permission=IntegerBoolField(required=True),
    bluetooth_active=IntegerBoolField(required=True),
    notification_permission=IntegerBoolField(required=True),
    exposure_notification=IntegerBoolField(required=True),
    last_risky_exposure_on=IsoDate(),
    salt=Base64String(
        required=True, min_encoded_length=config.SALT_LENGTH, max_encoded_length=config.SALT_LENGTH
    ),
    signed_attestation=fields.String(
        required=True, validate=Length(max=config.SIGNED_ATTESTATION_MAX_LENGTH)
    ),
)
@allows_dummy_requests
@inject_operational_info
async def post_android_operational_info(
    request: Request,
    operational_info: OperationalInfoDocument,
    salt: str,
    signed_attestation: str,
    last_risky_exposure_on: date,
    **kwargs: Any,
) -> HTTPResponse:
    """
    Check if the signed attestation is valid and the salt has not been used
    recently. In case of success save the operational_info.

    :param request: the HTTP request object.
    :param operational_info: The operational information to be saved.
    :param last_risky_exposure_on: the date on which the last Risky Exposure took place, if any.
    :param salt: a random string sent by the client to prevent replay attacks.
    :param signed_attestation: the payload generated by Google SafetyNet attestation API.
    :return: 200 in any case.
    """
    if await managers.analytics_redis.get(safety_net.get_redis_key(salt)):
        _LOGGER.warning(
            "Found previously used salt.",
            extra=dict(signed_attestation=signed_attestation, salt=salt),
        )
        return json_response(body=None, status=HTTPStatus.NO_CONTENT)

    verify_safety_net_attestation.delay(
        signed_attestation, salt, operational_info.to_dict(), last_risky_exposure_on.isoformat(),
    )

    return json_response(body=None, status=HTTPStatus.NO_CONTENT)
