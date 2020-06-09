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

from datetime import date
from http import HTTPStatus
from typing import Optional

from mongoengine import StringField
from sanic import Blueprint
from sanic.request import Request
from sanic.response import HTTPResponse
from sanic_openapi import doc

from immuni_analytics.core.managers import managers
from immuni_analytics.helpers.redis import get_authorized_tokens_redis_key_current_month
from immuni_analytics.models.operational_info import OperationalInfo as OperationalInfoDocument
from immuni_analytics.models.swagger import AuthorizationBody, OperationalInfo
from immuni_analytics.tasks.authorize_analytics_token import authorize_analytics_token
from immuni_analytics.tasks.store_operational_info import store_operational_info
from immuni_common.core.exceptions import SchemaValidationException
from immuni_common.helpers.sanic import json_response, validate
from immuni_common.helpers.swagger import doc_exception
from immuni_common.models.enums import Location, Platform
from immuni_common.models.marshmallow.fields import (
    Base64String,
    EnumField,
    IntegerBoolField,
    IsoDate,
    Province,
)
from immuni_common.models.swagger import HeaderImmuniContentTypeJson

bp = Blueprint("operational-info", url_prefix="/analytics")


@bp.route("apple/operational-info", methods=["POST"], version=1)
@doc.summary("Upload operational info (caller: Mobile Client.)")
@doc.description(
    "Check if the analytics_token is authorized to upload and save the operational info"
    " in the database."
)
@doc.consumes(doc.Boolean(name="Immuni-Dummy-Data", required=True), location="headers")
@doc.consumes(OperationalInfo, location="body")
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
    location=Location.HEADERS,
    is_dummy=IntegerBoolField(
        required=True,
        data_key="Immuni-Dummy-Data",
        allow_strings=True,
        description="Whether the current request is a dummy request. Dummy requests are ignored.",
    ),
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
async def post_operational_info(
    request: Request,
    is_dummy: bool,
    province: str,
    exposure_permission: bool,
    bluetooth_active: bool,
    notification_permission: bool,
    exposure_notification: bool,
    last_risky_exposure_on: date,
) -> HTTPResponse:
    """
    Check if the analytics_token is authorized and save the operational data
    in compliance with the rate limiting policy.
    """
    if is_dummy:
        return json_response(body=None, status=HTTPStatus.NO_CONTENT)

    if await managers.analytics_redis.srem(
        get_authorized_tokens_redis_key_current_month(exposure_notification), request.token
    ):
        store_operational_info.delay(
            OperationalInfoDocument(
                platform=Platform.IOS,
                province=province,
                exposure_permission=exposure_permission,
                bluetooth_active=bluetooth_active,
                notification_permission=notification_permission,
                exposure_notification=exposure_notification,
                last_risky_exposure_on=last_risky_exposure_on,
            ).to_mongo()
        )

    return json_response(body=None, status=HTTPStatus.NO_CONTENT)


@bp.route("apple/token", methods=["POST"], version=1)
@doc.summary("Authorize an analytics_token (caller: Mobile Client.)")
@doc.description(
    "Check if the device_token is genuine and allow the analytics_token to be used as"
    " an authorization token in compliance with the rate limiting policy."
)
@doc.consumes(doc.Boolean(name="Immuni-Dummy-Data", required=True), location="headers")
@doc.consumes(AuthorizationBody, location="body")
@doc.consumes(HeaderImmuniContentTypeJson(), location="header", required=True)
@doc_exception(SchemaValidationException)
@doc.response(
    HTTPStatus.NO_CONTENT.value, None, description="Well-formed request.",
)
@validate(
    location=Location.HEADERS,
    is_dummy=IntegerBoolField(
        required=True,
        data_key="Immuni-Dummy-Data",
        allow_strings=True,
        description="Whether the current request is a dummy request. Dummy requests are ignored.",
    ),
)
@validate(
    location=Location.JSON,
    platform=EnumField(enum=Platform),
    analytics_token=StringField(required=True),  # TODO: validate
    device_token=Base64String(required=True),  # TODO: validate
)
async def authorize_token(
    request: Request, is_dummy: bool, platform: Platform, analytics_token: str, device_token: str
) -> HTTPResponse:
    """
    Check if the device_token is genuine and, if so, authorize the analytics_token.
    """
    if is_dummy:
        return json_response(body=None, status=HTTPStatus.NO_CONTENT)

    if platform == Platform.IOS:
        authorize_analytics_token.delay(analytics_token, device_token)

    return json_response(body=None, status=HTTPStatus.NO_CONTENT)
