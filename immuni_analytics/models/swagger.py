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

from sanic_openapi import doc

from immuni_common.models.enums import Platform


class OperationalInfo:

    """
    Doc model for the Upload. This is simply a way to describe the Upload
    """

    platform = doc.String(
        "The device’s operating system (either iOS or Android)",
        choices=[p.value for p in Platform],
    )
    province = doc.String("The user's province of residence.")
    exposure_permission = doc.Integer(
        "A very rough geographical indication of where the device is generally located."
    )
    bluetooth_active = doc.Integer(
        "Whether the user has granted the App permission to use the Exposure Notifications "
        "framework. Without this permission the App won’t work."
    )
    notification_permission = doc.Integer(
        "Whether the user has Bluetooth turned on. If Bluetooth is turned off, the App won’t work."
    )
    exposure_notification = doc.Integer(
        "Whether the user has granted the App permission to display notifications. "
        "This is helpful to warn the user about an app malfunction, but it is not "
        "strictly necessary to receive exposure notifications."
    )
    last_risky_exposure_on = doc.Date(
        "Whether the user has received an exposure notification after being exposed to "
        "a user who tested positive to SARS-CoV-2."
    )


class AuthorizationBody:
    platform = doc.String(
        "The device’s operating system (either iOS or Android)",
        choices=[p.value for p in Platform],
    )
    analytics_token = doc.String(
        "The analytics_token to authorize for the operational_info uploads.",
    )
    device_token = doc.String(
        "The device token to check against Apple DeviceCheck or Android SafetyNet."
    )
