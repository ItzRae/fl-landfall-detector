"""Shared analysis for the dashboard and optional CSV exports."""
from pathlib import Path

import geopandas as gpd
import pandas as pd
from src.landfall import detect_hurricane_landfalls
from src.models import LandfallEvent
from src.parser import parse_hurdat


def analyze_inputs(hurdat_path: Path, boundary_path: Path):
    """Return source storms, Florida geometry, and chronological landfalls."""
    with hurdat_path.open("r") as file:
        storms = parse_hurdat(file.readlines())

    # Load FL's state boundary and align it with HURDAT lon/lat coordinates.
    states = gpd.read_file(boundary_path).to_crs("EPSG:4326")
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
            storm, florida_geom, neighbor_land_geom,
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

    return storms, florida_geom, landfall_events


def landfalls_dataframe(events: list[LandfallEvent]) -> pd.DataFrame:
    """Build the common dashboard and export schema, including empty results."""
    columns = ["storm_id", "storm_name", "landfall_datetime", "latitude", "longitude", "max_wind_kt"]
    rows = [(event.storm_id, event.storm_name, event.entry.timestamp,
             event.entry.point.y, event.entry.point.x, event.entry.wind)
            for event in events]
    frame = pd.DataFrame(rows, columns=columns)
    frame["landfall_datetime"] = pd.to_datetime(frame["landfall_datetime"])
    return frame
