
# Florida Hurricane Landfalls

An application for analyzing Atlantic HURDAT2 best-track data to identify
all hurricanes that made landfall in Florida from 1900 onward

For each qualifying landfall event, the application reports:
- Storm name
- Landfall date
- Maximum sustained wind speed

## Approach

The approach to this application goes as follows:

1. Parse the HURDAT2 dataset into structured storm and observation records
2. Reconstruct storm tracks from consecutive best-track positions
3. Compare track segments against Florida's geographic boundary
4. Identify crossings that represent entry from water onto Florida land
5. Determine whether the storm qualifies as a hurricane at landfall
6. Report the qualifying landfall events (name, date, max wind speed)

## Assumptions + Definitions

### Definitions
**Landfall:** A landfall is defined as the storm center crossing from water onto Florida land.

**Hurricane:** A qualifying event must occur while the cyclone is classified as a hurricane (`HU`) in HURDAT2.

### Multiple Landfalls
A storm may produce more than one Florida landfall. Each distinct water-to-land entry is treated as a separate event.

### Landfall intensity
How exactly do we assign hurricane status/wind when the coastline crossing falls between two observations? Policy TBD

## Architecture

```text
HURDAT2 data
    ↓
Parser
    ↓
Storm / Observation models
    ↓
Landfall detector ← Florida boundary geometry
    ↓
Candidate landfall crossings
    ↓
Hurricane-intensity filter
    ↓
LandfallEvent
    ↓
Report
    ↓
UI (optional if have time)
```

## Testing + Validation

Testing will focus on the parser and landfall detection logic independently so that geographic classification can be tested without relying on HURDAT2's provided landfall (`L`) identifier

Testing will include:
- HURDAT2 header and observation parsing
- Coordinate conversion
- Sentinel/missing value handling
- Water-to-land crossings
- Land-to-water crossings
- Offshore tracks
- Multiple landfalls
- Hurricane qualification at landfall

### Validation

The HURDAT2 `L` record identifier will not be used by the landfall detection
algorithm. However, after the geometric detection logic is implemented, it may be
used as an independent validation signal to check if the computed coastline crossings 
are consistent with NOAA's landfall flags - the `L` identifier will not determine whether an event is classified as a Florida landfall.
