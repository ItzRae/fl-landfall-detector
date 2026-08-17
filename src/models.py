from dataclasses import dataclass
from datetime import datetime
from shapely.geometry import Point

@dataclass
class Observation:
    timestamp: datetime
    status: str
    latitude: float
    longitude: float
    max_wind: int | None
    # Retained for validation only; not used for landfall detection
    record_identifier: str | None 

@dataclass
class Storm:
    id: str
    name: str
    observations: list[Observation]

@dataclass
class TrackEntry:
    point: Point
    fraction: float
    timestamp: datetime
    wind: float | None

@dataclass
class LandfallEvent:
    storm_id: str
    storm_name: str
    entry: TrackEntry