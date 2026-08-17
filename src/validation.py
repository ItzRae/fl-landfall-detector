from src.models import Storm, Observation
from src.landfall import HURRICANE_WIND_THRESHOLD

def get_hurricane_landfall_records(
    storm: Storm,
) -> list[Observation]:
    """Return HURDAT landfall records at hurricane strength for a storm.

    Args:
        storm: Parsed HURDAT storm containing track observations

    Returns:
        Observations explicitly marked with the HURDAT landfall indicator
        whose maximum sustained wind is at least hurricane strength
    """
    records = []

    for observation in storm.observations:
        if (observation.record_identifier != "L" or 
            observation.max_wind is None or 
            observation.max_wind < HURRICANE_WIND_THRESHOLD):
            continue

        records.append(observation)

    return records