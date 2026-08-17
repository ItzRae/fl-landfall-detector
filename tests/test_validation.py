
from datetime import datetime

from src.models import Observation, Storm
from src.validation import get_hurricane_landfall_records


def test_get_hurricane_landfall_records_filters_by_indicator_and_wind():
    """Return only hurricane-strength observations marked as landfalls"""

    storm = Storm(
        id="TEST001",
        name="TEST",
        observations=[
            Observation(
                timestamp=datetime(2000, 1, 1, 0, 0),
                status="HU",
                latitude=25.0,
                longitude=-80.0,
                max_wind=80,
                record_identifier="L",
            ),
            Observation(
                timestamp=datetime(2000, 1, 1, 1, 0),
                status="HU",
                latitude=25.1,
                longitude=-80.1,
                max_wind=64,
                record_identifier="L",
            ),
            Observation(
                timestamp=datetime(2000, 1, 1, 2, 0),
                status="TS",
                latitude=25.2,
                longitude=-80.2,
                max_wind=63,
                record_identifier="L",
            ),
            Observation(
                timestamp=datetime(2000, 1, 1, 3, 0),
                status="HU",
                latitude=25.3,
                longitude=-80.3,
                max_wind=100,
                record_identifier=None,
            ),
            Observation(
                timestamp=datetime(2000, 1, 1, 4, 0),
                status="HU",
                latitude=25.4,
                longitude=-80.4,
                max_wind=None,
                record_identifier="L",
            ),
        ],
    )

    records = get_hurricane_landfall_records(storm)

    assert len(records) == 2
    assert records[0].timestamp == datetime(2000, 1, 1, 0, 0)
    assert records[1].timestamp == datetime(2000, 1, 1, 1, 0)