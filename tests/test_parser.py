from datetime import datetime

import pytest

from src.parser import (
    parse_coordinate,
    parse_header,
    parse_hurdat,
    parse_observation,
)

def test_parse_header():
    """Test that a HURDAT2 header line is parsed correctly"""

    line = "AL172022,             NICOLE,     26,"

    storm_id, name, entry_count = parse_header(line)

    assert storm_id == "AL172022"
    assert name == "NICOLE"
    assert entry_count == 26

@pytest.mark.parametrize("value,expected", [
    ("80.3W", -80.3),
    ("27.6N", 27.6),
    ("25.0S", -25.0),
    ("40.0E", 40.0),
])
def test_parse_coordinate_sign_by_direction(value, expected):
    """Parse coordinate signs correctly for N/S/E/W."""

    assert parse_coordinate(value) == expected

def test_parse_coordinate_rejects_invalid_direction():
    """Test parsing coordinate raises ValueError for invalid direction character"""
    with pytest.raises(ValueError):
        parse_coordinate("80.3X")

def test_parse_observation():
    """Test that a HURDAT2 observation line is parsed correctly"""

    line = (
        "20221110, 0745, L, HU, 27.6N, 80.3W, 65, 980, "
        "390, 90, 180, 300, 80, 30, 20, 80, 20, 20, 0, 0, 20"
    )

    observation = parse_observation(line)

    assert observation.timestamp == datetime(2022, 11, 10, 7, 45)
    assert observation.status == "HU"
    assert observation.latitude == 27.6
    assert observation.longitude == -80.3
    assert observation.max_wind == 65
    assert observation.record_identifier == "L"

def test_parse_observation_blank_identifier_becomes_none():
    """Test that a HURDAT2 observation line with a blank record identifier is parsed correctly"""
    line = "20221110, 0600,  , HU, 27.3N, 79.8W, 65"

    observation = parse_observation(line)

    assert observation.record_identifier is None

def test_parse_observation_unassigned_wind_becomes_none():
    """Test that a HURDAT2 observation line with an unassigned maximum wind speed is parsed correctly"""

    line = "19670101, 0000,  , TD, 20.0N, 70.0W, -99"

    observation = parse_observation(line)

    assert observation.max_wind is None

def test_parse_hurdat_parses_multiple_storms():
    """Test that a HURDAT2 file with multiple storms is parsed correctly"""

    lines = [
        "AL012022, TESTONE, 2,\n",
        "20220101, 0000,  , TS, 25.0N, 75.0W, 50,\n",
        "20220101, 0600,  , HU, 26.0N, 76.0W, 65,\n",
        "AL022022, TESTTWO, 1,\n",
        "20220201, 0000, L, HU, 27.0N, 79.0W, 70,\n",
    ]

    storms = parse_hurdat(lines)

    assert len(storms) == 2
    assert storms[0].name == "TESTONE"
    assert len(storms[0].observations) == 2
    assert storms[1].name == "TESTTWO"
    assert len(storms[1].observations) == 1

def test_parse_hurdat_rejects_truncated_storm():
    """Test that a HURDAT2 file with a truncated storm raises a ValueError"""

    lines = [
        "AL012022, TESTONE, 2,\n",
        "20220101, 0000,  , TS, 25.0N, 75.0W, 50,\n",
    ]

    with pytest.raises(ValueError, match="Unexpected end of file"):
        parse_hurdat(lines)

