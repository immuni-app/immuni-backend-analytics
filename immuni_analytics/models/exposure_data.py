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
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from mongoengine import (
    DateField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    IntField,
    ListField,
    StringField,
    ValidationError,
)

from immuni_common.models.enums import TransmissionRiskLevel
from immuni_common.models.marshmallow.schemas import ExposureDetectionSummarySchema
from immuni_common.models.mongoengine.enum_field import EnumField

_LOGGER = logging.getLogger(__name__)


class ExposureInfo(EmbeddedDocument):
    """
    Embedded document representing the exposure info provided by the clients.
    """

    date = DateField(required=True)
    duration = IntField(required=True)
    attenuation_value = IntField(required=True)
    attenuation_durations = ListField(IntField(), required=True)
    transmission_risk_level = EnumField(TransmissionRiskLevel)
    total_risk_score = IntField(required=True)


class ExposureDetectionSummary(EmbeddedDocument):
    """
    Embedded document representing the exposure detection summaries provided by the clients.
    """

    date = DateField(required=True)
    matched_key_count = IntField(required=True)
    days_since_last_exposure = IntField(required=True)
    attenuation_durations = ListField(IntField(), required=True)
    maximum_risk_score = IntField(required=True)
    exposure_info = EmbeddedDocumentListField(ExposureInfo, required=False, default=[])


class ExposurePayload(Document):
    """
    Embedded document representing the payload of the ingested data.
    """

    province = StringField(required=True)
    # NOTE: the field is marked as not required to support any data forwarded by the
    # first version of the Exposure Ingestion Service, which did not include symptoms_started_on.
    # It will be changed as soon as all the old data have been collected.
    symptoms_started_on = DateField(required=False)
    exposure_detection_summaries = EmbeddedDocumentListField(
        ExposureDetectionSummary, required=False, default=[]
    )

    meta = {"indexes": ["province"]}

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> ExposurePayload:
        """
        Convert a dictionary into a validated ExposurePayload.

        :param payload: the dictionary to convert.
        :return: the corresponding ExposurePayload.
        """
        if (
            not (province := payload.get("province"))
            or (exposure_detection_summaries := payload.get("exposure_detection_summaries")) is None
        ):
            raise ValidationError()

        symptoms_started_on = payload.get("symptoms_started_on", None)

        return ExposurePayload(
            **{
                "province": province,
                "symptoms_started_on": symptoms_started_on,
                "exposure_detection_summaries": [
                    asdict(ExposureDetectionSummarySchema().load(e))
                    for e in exposure_detection_summaries
                ],
            }
        )

    @classmethod
    def delete_older_than(cls, reference_date: datetime) -> None:
        """
        Delete all objects older than the given datetime.
        :param reference_date: the datetime to check against.
        """
        objects = cls.objects.filter(id__lte=ObjectId.from_datetime(reference_date))
        count = objects.delete()

        _LOGGER.info(
            "ExposurePayload documents deletion completed.",
            extra={"n_deleted": count, "created_before": reference_date.isoformat()},
        )
