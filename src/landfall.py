from shapely.geometry import LineString, MultiPoint, MultiPolygon, Point, Polygon
from .models import Observation, TrackEntry, Storm

# The wind speed threshold for hurricane classification is 64 knots
HURRICANE_WIND_THRESHOLD = 64

def find_entry_points(
        storm_segment: LineString,
        land_geometry: Polygon,
    ) -> list[Point]:
    """Return points where a storm track segment enters land

    A land entry occurs when a track segment transitions from water (outside) 
    to land (inside or onto the coastline boundary). This includes segments 
    that terminate directly on the boundary after starting offshore.

    Args:
        storm_segment: Track segment between storm observations
        land_geometry: Polygon representing land

    Returns:
        Boundary points where the segment transitions from outside to inside (or onto the boundary).
    """

    # Find where the storm track intersects the land boundary
    intersection = storm_segment.intersection(land_geometry.boundary)

    if intersection.is_empty:
        return []

    # Normalize the intersection result into a list of individual crossing points
    if isinstance(intersection, Point):
        intersection_points = [intersection]
    elif isinstance(intersection, MultiPoint):
        intersection_points = list(intersection.geoms)
    else:
        # Ambiguous case: non-point intersection - track overlaps the coastline rather 
        # than crossing it at a discrete location, so fail explicitly
        raise ValueError(
            "Unsupported boundary intersection geometry "
            f"{intersection.geom_type!r}; expected Point or MultiPoint."
        )

    # Order crossings by their position along the storm's direction of travel
    sorted_points = sorted(
        intersection_points,
        key=lambda point: storm_segment.project(point, normalized=True),
    )

    entry_points = []
    epsilon = 1e-6

    for point in sorted_points:
        crossing_fraction = storm_segment.project(point, normalized=True)

        # Sample immediately before and after the crossing to determine whether
        # the storm transitions from water to land - consider lower + upper bounds
        before_fraction = max(crossing_fraction - epsilon, 0.0) 
        after_fraction = min(crossing_fraction + epsilon, 1.0) 

        before_point = storm_segment.interpolate(
            before_fraction,
            normalized=True,
        )
        after_point = storm_segment.interpolate(
            after_fraction,
            normalized=True,
        )

        before_is_inside = land_geometry.contains(before_point)
        after_is_inside = land_geometry.contains(after_point)

        # Detect special case where the segment terminates exactly on the coastline
        after_is_boundary = land_geometry.boundary.covers(after_point)

        # Exclude crossings at the segment start; they belong to the preceding segment
        normal_entry = (
            crossing_fraction > epsilon 
            and not before_is_inside
            and after_is_inside
        )

        endpoint_entry = (
            not before_is_inside
            and after_is_boundary
            and crossing_fraction >= 1.0 - epsilon
        )

        if normal_entry or endpoint_entry:
            entry_points.append(point)

    return entry_points

def interpolate_entry(
        start_obs: Observation,
        end_obs: Observation,
        point: Point,
    ) -> TrackEntry:
    """Interpolate the timestamp and wind speed at a landfall entry point.

    Args:
        start_obs: Observation at the start of the track segment
        end_obs: Observation at the end of the track segment
        point: Point where the storm track intersects land

    Returns:
        TrackEntry: Interpolated entry point, fraction, timestamp, and wind
    """

    obs_segment = LineString([
        (start_obs.longitude, start_obs.latitude),
        (end_obs.longitude, end_obs.latitude),
    ])

    crossing_fraction = obs_segment.project(point, normalized=True)

    # Use the crossing fraction along the observation segment to estimate
    # the landfall time and wind between the two recorded observations
    duration = end_obs.timestamp - start_obs.timestamp
    timestamp = start_obs.timestamp + (crossing_fraction * duration) 

    if start_obs.max_wind is None or end_obs.max_wind is None:
        estimated_wind = None
    else:
        wind_diff = end_obs.max_wind - start_obs.max_wind
        estimated_wind = start_obs.max_wind + (crossing_fraction * wind_diff )

    return TrackEntry(
        point=point,
        fraction=crossing_fraction,
        timestamp=timestamp,
        wind=estimated_wind,
    )
    

def detect_land_entries(
        storm: Storm, 
        land_geometry: Polygon | MultiPolygon
    ) -> list[TrackEntry]:
    """Detect geographic land entries along a storm track

    Args:
        storm: Storm object containing observations
        land_geometry: Polygon or MultiPolygon representing land

    Returns:
        List of TrackEntry objects representing land entries
    """

    entries: list[TrackEntry] = []

    # Iterate through each pair of consecutive observations to form track segments
    for i in range(len(storm.observations ) - 1):
        start_obs = storm.observations[i]
        end_obs = storm.observations[i + 1]

        segment = LineString([
            (start_obs.longitude, start_obs.latitude),
            (end_obs.longitude, end_obs.latitude),
        ])

        entry_points = find_entry_points(segment, land_geometry)

        for point in entry_points:
            entry = interpolate_entry(start_obs, end_obs, point)
            entries.append(entry)

    return entries


def is_hurricane_entry(entry: TrackEntry) -> bool:
    """Determine whether a land entry occurred at hurricane-strength winds

    Args:
        entry: TrackEntry object representing a land entry

    Returns:
        True if the storm was a hurricane (64 kt or more) at the time of land entry, 
        False otherwise
    """

    return entry.wind is not None and entry.wind >= HURRICANE_WIND_THRESHOLD


def detect_hurricane_landfalls(
        storm: Storm, 
        land_geometry: Polygon | MultiPolygon
    ) -> list[TrackEntry]:
    """Detect landfall entries where the storm was hurricane-strength

    Args:
        storm: Storm object containing observations
        land_geometry: Polygon or MultiPolygon representing land

    Returns:
        List of TrackEntry objects representing hurricane-strength land entries
    """

    all_entries = detect_land_entries(storm, land_geometry)
    hurricane_entries = [entry for entry in all_entries if is_hurricane_entry(entry)]

    return hurricane_entries