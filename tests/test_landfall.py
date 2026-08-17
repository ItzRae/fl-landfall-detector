from datetime import datetime

import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from src.landfall import (
    consolidate_same_component_reentries,
    detect_hurricane_landfalls,
    detect_land_entries,
    find_entry_points,
    interpolate_entry,
    is_hurricane_entry,
)
from src.models import Observation, Storm, TrackEntry

@pytest.fixture
def square():
    return Polygon([
        (0, 0),
        (4, 0),
        (4, 4),
        (0, 4),
    ])

def make_observation(
    timestamp,
    latitude,
    longitude,
    max_wind,
    status="HU",
    record_identifier=None,
):
    return Observation(
        timestamp=timestamp,
        status=status,
        latitude=latitude,
        longitude=longitude,
        max_wind=max_wind,
        record_identifier=record_identifier,
    )

def test_outside_to_inside_finds_one_entry(square):
    """Test that a storm segment crossing from outside -> inside a polygon finds one entry point"""

    segment = LineString([(-2, 2), (2, 2)])

    entries = find_entry_points(segment, square)
    assert len(entries) == 1

    # assert that the entry point is at (0, 2)
    assert entries[0].x == 0
    assert entries[0].y == 2


def test_inside_to_outside_finds_no_entry(square):
    """Test that a storm segment crossing from inside -> outside produces no new entry"""

    segment = LineString([(2, 2), (6, 2)])

    entries = find_entry_points(segment, square)
    assert len(entries) == 0


def test_outside_to_outside_no_crossing_finds_no_entry(square):
    """Test that a storm segment crossing from outside -> outside finds no entry point"""

    segment = LineString([(-2, 2), (-1, 2)])

    entries = find_entry_points(segment, square)
    assert len(entries) == 0


def test_clip_through_finds_one_entry(square):
    """Test that a storm segment crossing from outside -> inside -> outside 
    through a polygon finds one entry point"""

    segment = LineString([(-2, 2), (6, 2)])

    entries = find_entry_points(segment, square)
    assert len(entries) == 1

    assert entries[0].x == 0
    assert entries[0].y == 2
   

def test_inside_to_inside_finds_no_entry(square):
    """Test that a storm segment crossing from inside -> inside remains inside 
    and produces no new entry"""

    segment = LineString([(1, 1), (3, 3)])

    entries = find_entry_points(segment, square)

    assert len(entries) == 0


def test_outside_to_boundary_finds_one_entry(square):
    """Test that a storm segment crossing from outside -> boundary finds one entry point"""

    segment = LineString([(-2, 2), (0, 2)])

    entries = find_entry_points(segment, square)

    assert len(entries) == 1
    assert entries[0].x == 0
    assert entries[0].y == 2


def test_shared_boundary_is_not_double_counted(square):
    """Test that a storm segment crossing from outside -> boundary -> inside
    does not double count the entry point"""

    # outside, boundary
    segment_a = LineString([(-2, 2), (0, 2)])
    # boundary, inside
    segment_b = LineString([(0, 2), (2, 2)])

    entries_a = find_entry_points(segment_a, square)
    entries_b = find_entry_points(segment_b, square)

    # assert segment_a owns the landfall, and segment_b does not recount it
    assert len(entries_a) == 1
    assert entries_a[0].x == 0
    assert entries_a[0].y == 2
    assert len(entries_b) == 0


def test_interpolate_entry_midpoint():
    """Test interpolation of timestamp and wind speed at a land entry point between two observations"""
    start_obs = make_observation(
        timestamp=datetime(2026, 1, 1, 0, 0),
        latitude=2.0,
        longitude=-2.0,
        max_wind=60,
    )

    end_obs = make_observation(
        timestamp=datetime(2026, 1, 1, 2, 0),
        latitude=2.0,
        longitude=2.0,
        max_wind=80,
    )

    point = Point(0, 2)

    entry = interpolate_entry(start_obs, end_obs, point)

    assert entry.fraction == 0.5
    assert entry.timestamp == datetime(2026, 1, 1, 1, 0)
    assert entry.wind == 70


def test_interpolate_entry_missing_wind_returns_none():
    """Test that interpolation returns None for wind speed if either observation has missing wind data"""
    start_obs = make_observation(
        timestamp=datetime(2026, 1, 1, 0, 0),
        latitude=2.0,
        longitude=-2.0,
        max_wind=None,
    )

    end_obs = make_observation(
        timestamp=datetime(2026, 1, 1, 2, 0),
        latitude=2.0,
        longitude=2.0,
        max_wind=80,
    )

    point = Point(0, 2)

    entry = interpolate_entry(start_obs, end_obs, point)

    assert entry.wind is None


def test_detect_land_entries_finds_single_entry(square):
    """Test that detect_land_entries finds a single land entry for a storm track"""

    storm = Storm(
        id="TEST001",
        name="TEST",
        observations=[
            make_observation(
                timestamp=datetime(2026, 1, 1, 0, 0),
                latitude=2.0,
                longitude=-2.0,
                max_wind=60,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 1, 0),
                latitude=2.0,
                longitude=2.0,
                max_wind=70,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 2, 0),
                latitude=2.0,
                longitude=6.0,
                max_wind=65,
            ),
        ],
    )

    entries = detect_land_entries(storm, square)

    assert len(entries) == 1
    assert entries[0].point.x == 0
    assert entries[0].point.y == 2
    # Check that the timestamp is interpolated correctly between the first two observations
    assert entries[0].timestamp == datetime(2026, 1, 1, 0, 30)


def test_detect_land_entries_finds_multiple_entries(square):
    """Test that detect_land_entries finds multiple land entries for a storm track"""

    # Outside -> inside -> outside -> inside
    storm = Storm(
        id="TEST002",
        name="TEST",
        observations=[
            make_observation(
                timestamp=datetime(2026, 1, 1, 0, 0),
                latitude=2.0,
                longitude=-2.0,
                max_wind=60,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 1, 0),
                latitude=2.0,
                longitude=2.0,
                max_wind=70,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 2, 0),
                latitude=2.0,
                longitude=6.0,
                max_wind=65,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 3, 0),
                latitude=2.0,
                longitude=2.0,
                max_wind=75,
            ),
        ],
    )

    entries = detect_land_entries(storm, square)

    assert len(entries) == 2
    assert entries[0].point.x == 0
    assert entries[0].point.y == 2
    assert entries[1].point.x == 4
    assert entries[1].point.y == 2
    # Check entries are in chronological/track order
    assert entries[0].timestamp < entries[1].timestamp


@pytest.mark.parametrize(
    ("wind", "expected"),
    [
        (64, True),    # exact hurricane threshold
        (63.9, False), # just below threshold
        (80, True),    # clearly hurricane strength
        (None, False), # missing wind cannot qualify
    ],
)

def test_is_hurricane_entry(wind, expected):
    """Test that is_hurricane_entry correctly identifies hurricane-strength land entries"""

    entry = TrackEntry(
        point=Point(0, 0),
        fraction=0.5,
        timestamp=datetime(2026, 1, 1, 0, 0),
        wind=wind,
    )

    assert is_hurricane_entry(entry) == expected


def test_detect_hurricane_landfalls_includes_hurricane_strength_entry(square):
    """Test that detect_hurricane_landfalls correctly identifies hurricane-strength landfalls"""
    storm = Storm(
        id="TEST003",
        name="TEST",
        observations=[
            make_observation(
                timestamp=datetime(2026, 1, 1, 0, 0),
                latitude=2.0,
                longitude=-2.0,
                max_wind=70,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 1, 0),
                latitude=2.0,
                longitude=2.0,
                max_wind=70,
            ),
        ],
    )

    landfalls = detect_hurricane_landfalls(storm, square)

    assert len(landfalls) == 1
    assert landfalls[0].wind == 70


def test_detect_hurricane_landfalls_excludes_below_threshold_entry(square):
    """Test that detect_hurricane_landfalls correctly excludes below-threshold landfalls"""
    storm = Storm(
        id="TEST004",
        name="TEST",
        observations=[
            make_observation(
                timestamp=datetime(2026, 1, 1, 0, 0),
                status="TS",
                latitude=2.0,
                longitude=-2.0,
                max_wind=50,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 1, 0),
                status="TS",
                latitude=2.0,
                longitude=2.0,
                max_wind=50,
            ),
        ],
    )

    landfalls = detect_hurricane_landfalls(storm, square)

    assert len(landfalls) == 0


def test_detect_hurricane_landfalls_filters_multiple_entries(square):
    """Test that only hurricane-strength land entries are returned."""

    storm = Storm(
        id="TEST005",
        name="TEST",
        observations=[
            make_observation(
                timestamp=datetime(2026, 1, 1, 0, 0),
                latitude=2.0,
                longitude=-2.0,
                max_wind=70,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 1, 0),
                latitude=2.0,
                longitude=2.0,
                max_wind=70,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 2, 0),
                status="TS",
                latitude=2.0,
                longitude=6.0,
                max_wind=50,
            ),
            make_observation(
                timestamp=datetime(2026, 1, 1, 3, 0),
                status="TS",
                latitude=2.0,
                longitude=2.0,
                max_wind=50,
            ),
        ],
    )

    landfalls = detect_hurricane_landfalls(storm, square)

    assert len(landfalls) == 1
    assert landfalls[0].point.x == 0
    assert landfalls[0].point.y == 2
    assert landfalls[0].wind == 70

