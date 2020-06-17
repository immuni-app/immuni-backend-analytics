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

import logging
from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from mongoengine import Document

_LOGGER = logging.getLogger(__name__)


class RetentionPolicyCompliantDocument(Document):
    """
    Document base class providing a method to comply with the data retention policy.
    """

    meta: Dict[str, Any] = dict(allow_inheritance=True)

    @classmethod
    def delete_older_than(cls, reference_date: datetime) -> None:
        """
        Delete all objects older than the given datetime.

        :param reference_date: the datetime to check against.
        """
        objects = cls.objects.filter(id__lte=ObjectId.from_datetime(reference_date))
        count = objects.delete()

        _LOGGER.info(
            "%s documents deletion completed.",
            cls.__name__,
            extra={"n_deleted": count, "created_before": reference_date.isoformat()},
        )
