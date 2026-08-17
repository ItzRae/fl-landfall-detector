from pyproj import Transformer
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from shapely.ops import transform
from shapely.geometry import Point, Polygon, MultiPolygon

from src.landfall import HURRICANE_WIND_THRESHOLD
from src.models import Storm, Observation, LandfallEvent

# Validation-only tolerance accounting for differences between HURDAT
# reference coordinates and the modern Census Florida coastline
FLORIDA_LANDFALL_TOLERANCE_KM = 10.0

# Primary matches are based on time. A slightly wider time window is allowed
# only when the computed and reference landfalls are also geographically close
MAX_TIME_DIFFERENCE = timedelta(minutes=90)
EXTENDED_TIME_DIFFERENCE = timedelta(hours=3)
MAX_SPATIAL_DIFFERENCE_KM = 15.0

WGS84_TO_CONUS = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:5070",
    always_xy=True,
)

@dataclass
class LandfallMatch:
    computed: LandfallEvent
    reference: Observation
    time_difference: timedelta
    distance_km: float


def get_hurricane_landfall_records(
    storm: Storm,
) -> list[Observation]:
    """Return hurricane-strength HURDAT records marked as landfalls."""

    records = []

    for observation in storm.observations:
        if (observation.record_identifier != "L" or 
            observation.max_wind is None or 
            observation.max_wind < HURRICANE_WIND_THRESHOLD):
            continue

        records.append(observation)

    return records


def distance_to_florida_boundary_km(
    observation: Observation,
    florida_geometry: Polygon | MultiPolygon,
) -> float:
    """Return the observation's distance from the Florida boundary in km"""

    lat, lon = observation.latitude, observation.longitude
    point = Point(lon, lat)

    # Project both geometries into a metric CRS before measuring distance
    projected_point = transform(
        WGS84_TO_CONUS.transform,
        point,
    )

    projected_boundary = transform(
        WGS84_TO_CONUS.transform,
        florida_geometry.boundary,
    )

    distance_meters = projected_point.distance(
        projected_boundary
    )

    return distance_meters / 1000


def is_florida_landfall_record(
    observation: Observation,
    florida_geometry: Polygon | MultiPolygon,
) -> bool:
    """Return whether a HURDAT landfall record is close enough to Florida"""
    distance = distance_to_florida_boundary_km(
        observation,
        florida_geometry,
    )

    return distance <= FLORIDA_LANDFALL_TOLERANCE_KM


def get_florida_hurricane_landfall_records(
    storm: Storm,
    florida_geometry: Polygon | MultiPolygon,
) -> list[Observation]:
    """Return hurricane-strength HURDAT landfall records associated with Florida"""

    hurricane_landfalls = get_hurricane_landfall_records(storm)

    florida_landfalls = []

    for observation in hurricane_landfalls:
        if is_florida_landfall_record(
            observation,
            florida_geometry,
        ):
            florida_landfalls.append(observation)

    return florida_landfalls


def landfall_distance_km(
    computed: LandfallEvent,
    reference: Observation,
) -> float:
    """Return spatial distance between computed and reference landfalls in km."""
    computed_point = Point(
        computed.entry.point.x,
        computed.entry.point.y,
    )

    reference_point = Point(
        reference.longitude,
        reference.latitude,
    )

    projected_computed = transform(
        WGS84_TO_CONUS.transform,
        computed_point,
    )

    projected_reference = transform(
        WGS84_TO_CONUS.transform,
        reference_point,
    )

    return projected_computed.distance(projected_reference) / 1000


def match_landfall_events(
    computed_events: list[LandfallEvent],
    reference_events: list[tuple[str, Observation]],
) -> tuple[
    list[LandfallMatch],
    list[LandfallEvent],
    list[tuple[str, Observation]],
]:
    """Match computed landfalls to nearby HURDAT reference records. This
    function used only for validation and does not affect detection

    Matching happens within each storm - pairs within 90 minutes are eligible.
    A wider three-hour window is allowed when the locations are also within
    15 km. Eligible pairs are then assigned greedily from closest in time to
    farthest.

    Args:
        computed_events: Independently detected Florida hurricane landfalls.
        reference_events: Storm IDs paired with Florida HURDAT landfall records.

    Returns:
        Matched event pairs, unmatched computed events, and unmatched
        reference records. 
    """
    computed_by_storm = defaultdict(list)
    reference_by_storm = defaultdict(list)

    for event in computed_events:
        computed_by_storm[event.storm_id].append(event)

    for storm_id, observation in reference_events:
        reference_by_storm[storm_id].append(observation)

    matches = []
    unmatched_computed = []
    unmatched_reference = []


    storm_ids = set(computed_by_storm) | set(reference_by_storm)

    for storm_id in storm_ids:
        computed = computed_by_storm.get(storm_id, [])
        references = reference_by_storm.get(storm_id, [])

        candidate_pairs = []

        for computed_index, event in enumerate(computed):
            for reference_index, reference in enumerate(references):
                time_difference = abs(
                    event.entry.timestamp - reference.timestamp
                )

                distance_km = landfall_distance_km(
                    event,
                    reference,
                )

                is_time_match = (
                    time_difference <= MAX_TIME_DIFFERENCE
                )

                is_spatial_match = (
                    time_difference <= EXTENDED_TIME_DIFFERENCE
                    and distance_km <= MAX_SPATIAL_DIFFERENCE_KM
                )

                if is_time_match or is_spatial_match:
                    candidate_pairs.append(
                        (
                            time_difference,
                            distance_km,
                            computed_index,
                            reference_index,
                        )
                    )

        candidate_pairs.sort(
            key=lambda pair: (pair[0], pair[1])
        )

        matched_computed_indices = set()
        matched_reference_indices = set()

        for (
            time_difference,
            distance_km,
            computed_index,
            reference_index,
        ) in candidate_pairs:
            if computed_index in matched_computed_indices:
                continue

            if reference_index in matched_reference_indices:
                continue

            matches.append(
                LandfallMatch(
                    computed=computed[computed_index],
                    reference=references[reference_index],
                    time_difference=time_difference,
                    distance_km=distance_km,
                )
            )

            matched_computed_indices.add(computed_index)
            matched_reference_indices.add(reference_index)

        for index, event in enumerate(computed):
            if index not in matched_computed_indices:
                unmatched_computed.append(event)

        for index, reference in enumerate(references):
            if index not in matched_reference_indices:
                unmatched_reference.append(
                    (storm_id, reference)
                )

    return matches, unmatched_computed, unmatched_reference

