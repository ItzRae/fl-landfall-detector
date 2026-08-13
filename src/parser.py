from datetime import datetime
from .models import Observation, Storm

def parse_header(line: str) -> tuple[str, str, int]:
    """Parse a HURDAT2 storm header."""
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 3:
        raise ValueError("Header line must contain storm ID, name, and entry count.")
    
    storm_id = parts[0]
    storm_name = parts[1]
    entry_count = int(parts[2])
    
    return storm_id, storm_name, entry_count


def parse_coordinate(value: str) -> float:
    """Convert a HURDAT2 coordinate to signed decimal degrees."""

    value = value.strip() 

    if len(value) < 2:
        raise ValueError(f"Invalid coordinate value: {value}")

    signs = {
        'N': 1, 
        'E': 1, 
        'S': -1,
        'W': -1
    }
    coordinate = float(value[:-1])  
    direction = value[-1].upper()  


    # HURDAT2 always encodes magnitude + direction separately (e.g. "25.4N"),
    # so a negative numeric value means an upstream parsing error
    if direction not in signs or coordinate < 0:
        raise ValueError(f"Invalid coordinate value: {value}")

    return coordinate * signs[direction]


def parse_observation(line: str) -> Observation:
    """Parse a HURDAT2 best-track observation."""

    parts = [part.strip() for part in line.split(",")]

    if len(parts) < 7:
        raise ValueError("Observation line must contain at least 7 fields.")

    date = parts[0]
    time = parts[1]

    timestamp = datetime.strptime(date + time, "%Y%m%d%H%M")

    # Retained for independent validation not for landfall detection
    record_identifier = parts[2] if parts[2] else None
    status = parts[3]

    latitude = parse_coordinate(parts[4])
    longitude = parse_coordinate(parts[5])
    
    wind_value = int(parts[6])

    # HURDAT2 uses -99 for unassigned wind values; map it to None for downstream safety
    max_wind = None if wind_value == -99 else wind_value

    return Observation(
        timestamp=timestamp,
        status=status,
        latitude=latitude,
        longitude=longitude,
        max_wind=max_wind,
        record_identifier=record_identifier
    )


def parse_hurdat(lines: list[str]) -> list[Storm]:
    """Parse HURDAT2 lines into storms and their observations."""

    if not lines:
        raise ValueError("Input lines are empty.")

    storms: list[Storm] = []
    index = 0

    while index < len(lines):

        storm_id, storm_name, entry_count = parse_header(lines[index])
        index += 1

        observations: list[Observation] = []

        # HURDAT2 headers declare exactly how many observation rows follow
        for _ in range(entry_count):
            if index >= len(lines):
                raise ValueError(
                    f"Unexpected end of file while parsing {storm_id}. "
                    f"Expected {entry_count} observations."
                )
            observation = parse_observation(lines[index])
            observations.append(observation)
            index += 1
        
        storms.append(
            Storm(
                id=storm_id,
                name=storm_name,
                observations=observations,
            )
        )

    return storms


