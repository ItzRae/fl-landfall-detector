import pytest
from shapely.geometry import Polygon, LineString

from src.landfall import find_entry_points

@pytest.fixture
def square():
    return Polygon([
        (0, 0),
        (4, 0),
        (4, 4),
        (0, 4),
    ])


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
