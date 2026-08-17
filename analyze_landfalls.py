from pathlib import Path
import csv
import statistics
import geopandas as gpd

from src.landfall import detect_hurricane_landfalls
from src.parser import parse_hurdat
from src.models import LandfallEvent
from src.validation import get_florida_hurricane_landfall_records, match_landfall_events

HURDAT_PATH = Path("data/hurdat2-1851-2022-042723.txt")
BOUNDARY_PATH = Path("data/boundaries/cb_2025_us_state_500k.shp")
OUTPUT_PATH = Path("output/florida_hurricane_landfalls.csv")
VALIDATION_OUTPUT_PATH = Path("output/validation_summary.csv")

def write_landfalls_csv(
    events: list[LandfallEvent],
    output_path: Path,
) -> None:
    """Write computed Florida hurricane landfalls to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            "storm_id",
            "storm_name",
            "landfall_datetime",
            "latitude",
            "longitude",
            "max_wind_kt",
        ])

        for event in events:
            writer.writerow([
                event.storm_id,
                event.storm_name,
                event.entry.timestamp.isoformat(),
                event.entry.point.y,
                event.entry.point.x,
                event.entry.wind,
            ])

    print(
    f"Wrote {len(events)} computed landfall candidates "
    f"to {OUTPUT_PATH}"
    )

def write_validation_summary_csv(
    matches,
    unmatched_computed,
    unmatched_reference,
    reference_events,
    computed_events,
    output_path: Path,
) -> None:
    """Write summary metrics from independent HURDAT2 validation"""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    time_errors_min = [
        match.time_difference.total_seconds() / 60
        for match in matches
    ]

    spatial_errors_km = [
        match.distance_km
        for match in matches
    ]

    reference_coverage = (
        len(matches) / len(reference_events) * 100
        if reference_events
        else 0
    )

    computed_match_rate = (
        len(matches) / len(computed_events) * 100
        if computed_events
        else 0
    )

    with output_path.open("w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            "reference_events",
            "computed_landfalls",
            "matched",
            "unmatched_computed",
            "unmatched_reference",
            "reference_coverage_pct",
            "computed_match_rate_pct",
            "median_time_difference_min",
            "mean_time_difference_min",
            "median_spatial_difference_km",
            "mean_spatial_difference_km",
        ])

        writer.writerow([
            len(reference_events),
            len(computed_events),
            len(matches),
            len(unmatched_computed),
            len(unmatched_reference),
            round(reference_coverage, 1),
            round(computed_match_rate, 1),
            round(statistics.median(time_errors_min), 1),
            round(statistics.mean(time_errors_min), 1),
            round(statistics.median(spatial_errors_km), 1),
            round(statistics.mean(spatial_errors_km), 1),
        ])

    print(
        f"Wrote validation summary to {output_path}"
    )


def main():
    """Run the full HURDAT2 analysis to identify Florida hurricane landfall events.

    This script loads Atlantic HURDAT2 storm tracks and the Florida state boundary,
    applies the geometry-based landfall detector, and reports qualifying hurricane
    landfalls from 1900 onward
    """

    with HURDAT_PATH.open("r") as file:
        storms = parse_hurdat(file.readlines())

    # Load FL's state boundary and align it with HURDAT lon/lat coordinates.
    states = gpd.read_file(BOUNDARY_PATH).to_crs("EPSG:4326")
    florida = states[states["NAME"] == "Florida"]
    florida_geom = florida.geometry.iloc[0]

    # Consider hurricanes entering from FL's neighbors
    neighboring_states = states[
    states["NAME"].isin(["Alabama", "Georgia"])
]
    neighbor_land_geom = neighboring_states.geometry.union_all()

    landfall_events: list[LandfallEvent] = []

    for storm in storms:
        entries = detect_hurricane_landfalls(
                    storm, 
                    florida_geom,
                    neighbor_land_geom,
                )

        for entry in entries:
            if entry.timestamp.year >= 1900:
                landfall_events.append(
                    LandfallEvent(
                        storm_id=storm.id,
                        storm_name=storm.name,
                        entry=entry,
                    )
                )

    # Keep report output deterministic and chronological
    landfall_events.sort(key=lambda event: event.entry.timestamp)

    write_landfalls_csv(
        landfall_events,
        OUTPUT_PATH,
    )   

    # Build HURDAT2 L-based record-identifier events separately for independent validation
    reference_events = []

    for storm in storms:
        records = get_florida_hurricane_landfall_records(
            storm,
            florida_geom,
        )

        for record in records:
            if record.timestamp.year >= 1900:
                reference_events.append(
                    (storm.id, record)
                )

    reference_events.sort(
        key=lambda item: item[1].timestamp
    )

    matches, unmatched_computed, unmatched_reference = match_landfall_events(
        landfall_events,
        reference_events,
    )

    write_validation_summary_csv(
        matches,
        unmatched_computed,
        unmatched_reference,
        reference_events,
        landfall_events,
        VALIDATION_OUTPUT_PATH,
    )   
   

if __name__ == "__main__":
    main()