from datetime import datetime, timedelta

import geopandas as gpd
import pytest
from shapely.geometry import box

from src.analysis import detect_state_landfalls
from src.models import Observation, Storm


def track(points, wind=80):
    return Storm('TEST', 'TEST', [
        Observation(datetime(2000, 1, 1) + timedelta(hours=i), 'HU', y, x, wind, None)
        for i, (x, y) in enumerate(points)
    ])


def boundaries(second):
    return gpd.GeoDataFrame({'NAME': ['A', 'B']}, geometry=[box(0, 0, 2, 2), second], crs='EPSG:4326')


def test_inland_crossing_excluded_even_when_neighbor_unselected():
    states = boundaries(box(2, 0, 4, 2))
    storm = track([(-1, 1), (1, 1), (3, 1)])
    result = detect_state_landfalls([storm], states, ['A', 'B'])
    assert result.state.tolist() == ['A']
    assert detect_state_landfalls([storm], states, ['B']).empty


def test_separate_water_entries_retained_for_each_state():
    result = detect_state_landfalls([track([(-1, 1), (5, 1)])], boundaries(box(3, 0, 4, 2)), ['B', 'A', 'A'])
    assert result.state.tolist() == ['A', 'B']
    assert result.longitude.tolist() == [0, 3]
    assert result.landfall_datetime.is_monotonic_increasing


def test_empty_selection_and_weak_storm():
    states = boundaries(box(3, 0, 4, 2))
    assert detect_state_landfalls([], states, []).empty
    assert detect_state_landfalls([track([(-1, 1), (5, 1)], 50)], states, ['A', 'B']).empty


def test_missing_state_rejected():
    with pytest.raises(ValueError, match='Missing state boundaries'):
        detect_state_landfalls([], boundaries(box(3, 0, 4, 2)), ['Missing'])
