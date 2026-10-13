from pathlib import Path
import csv
import statistics

from src.analysis import analyze_inputs, landfalls_dataframe
from src.data_sources import ROOT, input_paths
from src.models import LandfallEvent
from src.validation import get_florida_hurricane_landfall_records, match_landfall_events

OUTPUT_PATH = ROOT / Path("output/florida_hurricane_landfalls.csv")
VALIDATION_OUTPUT_PATH = ROOT / Path("output/validation_summary.csv")

def write_landfalls_csv(
    events: list[LandfallEvent],
    output_path: Path,
) -> None:
    """Write computed Florida hurricane landfalls to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame = landfalls_dataframe(events)
    frame["landfall_datetime"] = frame["landfall_datetime"].map(lambda value: value.isoformat())
    frame.to_csv(output_path, index=False)
    print(f"Wrote {len(events)} computed landfall candidates to {output_path}")


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
            round(statistics.median(time_errors_min), 1) if matches else None,
            round(statistics.mean(time_errors_min), 1) if matches else None,
            round(statistics.median(spatial_errors_km), 1) if matches else None,
            round(statistics.mean(spatial_errors_km), 1) if matches else None,
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

    storms, florida_geom, landfall_events = analyze_inputs(*input_paths())

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
