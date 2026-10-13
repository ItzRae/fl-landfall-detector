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


COASTAL_STATES = (
    "Alabama", "Connecticut", "Delaware", "Florida", "Georgia", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Mississippi", "New Hampshire",
    "New Jersey", "New York", "North Carolina", "Rhode Island",
    "South Carolina", "Texas", "Virginia",
)


def detect_state_landfalls(storms, states, selected_states, start_year=1900):
    """Attribute coastal entries to states, excluding all adjacent US land.

    Unselected neighbors still count as land. The boundary dataset must include
    all US states; international land is not represented by this dataset.
    """
    selected_states = tuple(dict.fromkeys(selected_states))
    missing = set(selected_states) - set(states["NAME"])
    if missing:
        raise ValueError(f"Missing state boundaries: {', '.join(sorted(missing))}")
    frames = []
    for name in selected_states:
        geometry = states.loc[states["NAME"] == name].geometry.union_all()
        # Limit the union to nearby states, including neighbors not selected.
        others = states[(states["NAME"] != name) & states.geometry.intersects(geometry.envelope)]
        excluded = others.geometry.union_all() if not others.empty else None
        minx, miny, maxx, maxy = geometry.bounds
        events = []
        for storm in storms:
            observations = storm.observations
            if not observations or observations[-1].timestamp.year < start_year:
                continue
            xs = [obs.longitude for obs in observations]
            ys = [obs.latitude for obs in observations]
            if max(xs) < minx or min(xs) > maxx or max(ys) < miny or min(ys) > maxy:
                continue
            for entry in detect_hurricane_landfalls(storm, geometry, excluded):
                if entry.timestamp.year >= start_year:
                    events.append(LandfallEvent(storm.id, storm.name, entry))
        frame = landfalls_dataframe(events)
        frame["state"] = name
        frames.append(frame)
    if not frames:
        return landfalls_dataframe([]).assign(state=pd.Series(dtype="str"))
    return pd.concat(frames, ignore_index=True).sort_values(
        ["landfall_datetime", "storm_id", "state"], ignore_index=True,
    )


def analyze_states(hurdat_path: Path, boundary_path: Path, selected_states=COASTAL_STATES):
    """Load Atlantic tracks and produce a combined table for coastal states."""
    storms = parse_hurdat(hurdat_path.read_text().splitlines())
    states = gpd.read_file(boundary_path).to_crs("EPSG:4326")
    return detect_state_landfalls(storms, states, selected_states)
