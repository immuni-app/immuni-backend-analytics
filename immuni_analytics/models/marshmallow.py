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

from marshmallow import Schema, ValidationError
from marshmallow.fields import String
from marshmallow.validate import Regexp

from immuni_analytics.core import config
from immuni_common.core.exceptions import SchemaValidationException


class AnalyticsToken(String):
    """
    Validate a string to be a possible analytics token.
    """

    def __init__(self) -> None:
        super().__init__(
            required=True, validate=Regexp(rf"^[a-f0-9]{{{config.ANALYTICS_TOKEN_SIZE}}}$")
        )


def validate_analytics_token_from_bearer(bearer_token: str) -> str:
    """
    Validate the given bearer token is a possible analytics token, and return it.

    :param bearer_token: the bearer token to validate.
    :return: the validated analytics token (unchanged bearer token).
    """
    schema = Schema.from_dict(dict(analytics_token=AnalyticsToken()))
    try:
        # pylint: disable=no-member
        return schema().load(dict(analytics_token=bearer_token))["analytics_token"]
    except ValidationError as exc:
        raise SchemaValidationException(exc.messages) from exc
