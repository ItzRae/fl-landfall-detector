
from datetime import datetime

from src.models import LandfallEvent, Observation, Storm, TrackEntry, Point
from src.validation import (
    get_hurricane_landfall_records,
    match_landfall_events,
)

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


def test_match_landfall_events_matches_nearby_event():
    """Match a computed landfall with a nearby reference record."""

    computed = LandfallEvent(
        storm_id="TEST002",
        storm_name="TEST",
        entry=TrackEntry(
            point=Point(-80.0, 25.0),
            fraction=0.5,
            timestamp=datetime(2000, 1, 1, 1, 0),
            wind=80,
        ),
    )

    reference = Observation(
        timestamp=datetime(2000, 1, 1, 1, 30),
        status="HU",
        latitude=25.0,
        longitude=-80.0,
        max_wind=80,
        record_identifier="L",
    )

    matches, unmatched_computed, unmatched_reference = (
        match_landfall_events(
            [computed],
            [("TEST002", reference)],
        )
    )

    assert len(matches) == 1
    assert unmatched_computed == []
    assert unmatched_reference == []


def test_match_landfall_events_rejects_distant_event():
    """Leave computed and reference events unmatched when they are too far apart"""

    computed = LandfallEvent(
        storm_id="TEST001",
        storm_name="TEST",
        entry=TrackEntry(
            point=Point(-80.0, 25.0),
            fraction=0.5,
            timestamp=datetime(2000, 1, 1, 1, 0),
            wind=80,
        ),
    )

    reference = Observation(
        timestamp=datetime(2000, 1, 1, 6, 0),
        status="HU",
        latitude=28.0,
        longitude=-83.0,
        max_wind=80,
        record_identifier="L",
    )

    matches, unmatched_computed, unmatched_reference = (
        match_landfall_events(
            [computed],
            [("TEST001", reference)],
        )
    )

    assert matches == []
    assert unmatched_computed == [computed]
    assert unmatched_reference == [("TEST001", reference)]


def test_match_landfall_events_matches_reference_only_once():
    """Prevent one reference event from matching multiple computed landfalls"""

    computed_a = LandfallEvent(
        storm_id="TEST001",
        storm_name="TEST",
        entry=TrackEntry(
            point=Point(-80.0, 25.0),
            fraction=0.5,
            timestamp=datetime(2000, 1, 1, 1, 0),
            wind=80,
        ),
    )

    computed_b = LandfallEvent(
        storm_id="TEST001",
        storm_name="TEST",
        entry=TrackEntry(
            point=Point(-80.01, 25.01),
            fraction=0.5,
            timestamp=datetime(2000, 1, 1, 1, 20),
            wind=80,
        ),
    )

    reference = Observation(
        timestamp=datetime(2000, 1, 1, 1, 10),
        status="HU",
        latitude=25.0,
        longitude=-80.0,
        max_wind=80,
        record_identifier="L",
    )

    matches, unmatched_computed, unmatched_reference = (
        match_landfall_events(
            [computed_a, computed_b],
            [("TEST001", reference)],
        )
    )

    assert len(matches) == 1
    assert len(unmatched_computed) == 1
    assert unmatched_reference == []