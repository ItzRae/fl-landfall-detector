from pathlib import Path
import csv
import geopandas as gpd

from src.landfall import detect_hurricane_landfalls
from src.parser import parse_hurdat
from src.models import LandfallEvent
from src.validation import get_florida_hurricane_landfall_records, inspect_unmatched_reference, match_landfall_events

HURDAT_PATH = Path("data/hurdat2-1851-2022-042723.txt")
BOUNDARY_PATH = Path("data/boundaries/cb_2025_us_state_500k.shp")
OUTPUT_PATH = Path("output/florida_hurricane_landfalls.csv")
VALIDATION_OUTPUT_PATH = Path("output/validation_matches.csv")

def write_landfalls_csv(
        events: list[LandfallEvent],
        output_path: Path,
) -> None:
    """Write computed Florida hurricane landfall candidates to CSV."""
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

def write_validation_matches_csv(
    matches,
    output_path: Path,
) -> None:
    """Write computed/reference landfall matches used for validation."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            "storm_id",
            "storm_name",
            "computed_datetime",
            "reference_datetime",
            "time_difference_min",
            "computed_latitude",
            "computed_longitude",
            "reference_latitude",
            "reference_longitude",
            "distance_km",
        ])

        for match in matches:
            writer.writerow([
                match.computed.storm_id,
                match.computed.storm_name,
                match.computed.entry.timestamp.isoformat(),
                match.reference.timestamp.isoformat(),
                match.time_difference.total_seconds() / 60,
                match.computed.entry.point.y,
                match.computed.entry.point.x,
                match.reference.latitude,
                match.reference.longitude,
                match.distance_km,
            ])

    print(
        f"Wrote {len(matches)} matched landfall candidates to 'L' record-identifiers"
        f"to {OUTPUT_PATH}"
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

    landfall_events: list[LandfallEvent] = []

    for storm in storms:
        entries = detect_hurricane_landfalls(storm, florida_geom)

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

    write_validation_matches_csv(
        matches,
        VALIDATION_OUTPUT_PATH,
    )
   

if __name__ == "__main__":
    main()