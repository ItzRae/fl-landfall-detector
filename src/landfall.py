from shapely.geometry import LineString, MultiPoint, Point, Polygon


def find_entry_points(
    storm_segment: LineString,
    land_geometry: Polygon,
) -> list[Point]:
    """Return points where a storm track segment enters land

    A land entry occurs when a track segment transitions from water (outside) 
    to land (inside or onto the coastline boundary). This includes segments 
    that terminate directly on the boundary after starting offshore.

    Args:
        storm_segment: Track segment between storm observations.
        land_geometry: Polygon representing land.

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