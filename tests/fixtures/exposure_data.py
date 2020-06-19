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

from copy import deepcopy
from typing import Any, Callable, Dict, List

from pytest import fixture

from immuni_analytics.models.exposure_data import ExposurePayload


@fixture
def exposure_data_dict() -> Dict[str, Any]:
    return dict(
        version=1,
        payload=dict(
            province="AG",
            symptoms_started_on="2020-01-12",
            exposure_detection_summaries=[
                {
                    "date": "2020-01-11",
                    "matched_key_count": 2,
                    "days_since_last_exposure": 1,
                    "attenuation_durations": [300, 0, 0],
                    "maximum_risk_score": 4,
                    "exposure_info": [
                        {
                            "date": "2020-01-11",
                            "duration": 5,
                            "attenuation_value": 45,
                            "attenuation_durations": [300, 0, 0],
                            "transmission_risk_level": 4,
                            "total_risk_score": 4,
                        },
                        {
                            "date": "2020-01-11",
                            "duration": 5,
                            "attenuation_value": 45,
                            "attenuation_durations": [300, 0, 0],
                            "transmission_risk_level": 2,
                            "total_risk_score": 4,
                        },
                    ],
                },
                {
                    "date": "2020-01-12",
                    "matched_key_count": 2,
                    "days_since_last_exposure": 1,
                    "attenuation_durations": [300, 0, 0],
                    "maximum_risk_score": 4,
                    "exposure_info": [
                        {
                            "date": "2020-01-12",
                            "duration": 5,
                            "attenuation_value": 45,
                            "attenuation_durations": [300, 0, 0],
                            "transmission_risk_level": 2,
                            "total_risk_score": 4,
                        }
                    ],
                },
            ],
        ),
    )


@fixture
def generate_redis_data(
    exposure_data_dict: Dict[str, Any]
) -> Callable[[int], List[Dict[str, Any]]]:
    def _generate_redis_data(length: int) -> List[Dict[str, Any]]:
        return [deepcopy(exposure_data_dict) for _ in range(length)]

    return _generate_redis_data


@fixture
def generate_mongo_data(exposure_data_dict: Dict[str, Any]) -> Callable[[int], None]:
    def _generate_mongo_data(length: int) -> None:
        for _ in range(length):
            ExposurePayload.from_dict(exposure_data_dict["payload"]).save()

    return _generate_mongo_data
