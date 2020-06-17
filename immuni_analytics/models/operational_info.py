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

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional

from mongoengine import BooleanField, DateField, StringField

from immuni_analytics.models.data_retention_document import DataRetentionDocument
from immuni_common.models.enums import Platform
from immuni_common.models.mongoengine.enum_field import EnumField

_LOGGER = logging.getLogger(__name__)


class OperationalInfo(DataRetentionDocument):
    """
    Model representing the operational information to save in the database.
    """

    platform: Platform = EnumField(enum=Platform, required=True)
    province: str = StringField(required=True)
    exposure_permission: bool = BooleanField(required=True)
    bluetooth_active: bool = BooleanField(required=True)
    notification_permission: bool = BooleanField(required=True)
    exposure_notification: bool = BooleanField(required=True)
    last_risky_exposure_on: Optional[date] = DateField(required=False)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the mongo document into a serializable dictionary.

        :return: a dictionary representing the OperationalInfo document.
        """
        return dict(
            platform=self.platform.value,  # pylint: disable=no-member
            province=self.province,
            exposure_permission=self.exposure_permission,
            bluetooth_active=self.bluetooth_active,
            notification_permission=self.notification_permission,
            exposure_notification=self.exposure_notification,
            # pylint: disable=no-member
            last_risky_exposure_on=self.last_risky_exposure_on.isoformat()
            if self.last_risky_exposure_on
            else None,
        )

    @staticmethod
    def from_dict(value: Dict[str, Any]) -> OperationalInfo:
        """
        Convert a dictionary into an OperationalInfo document.

        :param value:a dictionary representing the OperationalInfo document.
        :return: an OperationalInfo document generated from the given dictionary.
        """
        return OperationalInfo(
            platform=Platform(value["platform"]),
            province=value["province"],
            exposure_permission=value["exposure_permission"],
            bluetooth_active=value["bluetooth_active"],
            notification_permission=value["notification_permission"],
            exposure_notification=value["exposure_notification"],
            last_risky_exposure_on=date.fromisoformat(value["last_risky_exposure_on"])
            if value.get("last_risky_exposure_on")
            else None,
        )
