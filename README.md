
# Florida Hurricane Landfalls

An application for analyzing Atlantic HURDAT2 best-track data to identify
hurricanes that made landfall in Florida from 1900 onward using independent
geometry-based landfall detection.

For each qualifying landfall, the application reports:
- Storm name
- Landfall date and estimated UTC time
- Estimated maximum sustained wind speed at landfall
- Optional landfall coordinates

## Running the application

A deployed version of the application is available here:

https://fl-landfall-detector.streamlit.app/

The interface provides:

- Year, storm, and minimum-wind filters
- Summary metrics
- Interactive landfall map
- Filterable landfall results table

### Running locally

From the repository root, first generate the landfall and validation outputs:

```bash
python analyze_landfalls.py
```

Running the analysis produces:

- `output/florida_hurricane_landfalls.csv` — independently detected Florida
  hurricane landfall events
- `output/validation_summary.csv` — summary metrics from the independent
HURDAT2 validation comparison

The validation output does not affect which events are detected or included
in the primary landfall results to inspect how my own system diverges from HURDAT's 
landfall classification. 

Then launch the Streamlit interface:

```bash
streamlit run app.py
```

---

### Approach

The approach to this application goes as follows:

1. Parse the HURDAT2 dataset into structured storm and observation records
2. Reconstruct storm tracks from consecutive best-track positions
3. Compare track segments against Florida's geographic boundary
4. Identify crossings that represent entry from water onto Florida land
5. Determine whether the storm qualifies as a hurricane at landfall
6. Report the qualifying landfall events (name, date, max wind speed)

### Assumptions + Definitions

#### Definitions

##### Landfall

**A Florida landfall in this application is detected when the storm's surface center intersects
with the coastline, according to the Nathional Hurrican Center's definition of landfall.** Consecutive HURDAT2 best-track observations are connected by straight track segments, and a Florida landfall is detected whenever the reconstructed storm-center track transitions from water onto the selected Florida land geometry

HURDAT2 latitude and longitude observations are treated as estimates of the
storm-center position. When a coastline crossing occurs between observations,
the center track is linearly interpolated between the surrounding positions.

The detector samples immediately before and after each boundary crossing to
distinguish water-to-land entries from exits or coastline touches. Crossings
from neighboring-state land in Alabama or Georgia into Florida are excluded,
since those are interstate crossings rather than landfalls.

Each distinct water-to-land crossing is retained as a Florida landfall.

##### Qualifying hurricane landfall

A detected landfall qualifies for the hurricane results when the estimated
**maximum sustained wind at the coastline crossing is at least 64 kt (74 mph)**.

This qualification is applied after the geometric landfall is detected. The
HURDAT2 `L` landfall identifier is not used to determine whether a crossing
occurred or whether it qualifies.

##### Multiple Landfalls
A storm may produce more than one Florida landfall. Each distinct water-to-land entry is treated as a separate event.

##### Landfall time + intensity
**How exactly do we assign hurricane status/wind when the coastline crossing falls between two observations?**
Because HURDAT2 observations are generally spaced several hours apart, the exact coastline crossing often occurs between observations.

The application estimates the crossing time and maximum sustained wind using linear 
interpolation along the track segment between the surrounding observations. This assumes 
approximately linear storm motion and wind change over that interval.

### Architecture

```text
HURDAT2 data
    ↓
Parser
    ↓
Storm / Observation models
    ↓
Storm-center track segments
    ↓
Landfall detector ← Florida geometry + neighboring-state land geometry
    ↓
Detected water-to-land crossings
    ↓
Crossing time + wind interpolation
    ↓
Hurricane-intensity filter (≥ 64 kt)
    ↓
LandfallEvent
    ↓
CSV output
    ↓
Streamlit UI
```

### Testing + Validation

Testing will focus on the parser and landfall detection logic independently so that geographic classification can be tested without relying on HURDAT2's provided landfall (`L`) identifier

Testing includes:
- HURDAT2 header and observation parsing
- Coordinate conversion
- Sentinel/missing value handling
- Water-to-land crossings
- Land-to-water crossings
- Interstate land crossings
- Offshore tracks
- Multiple landfalls
- Hurricane qualification at landfall
- Shared-boundary and segment-endpoint behavior

#### Validation

The HURDAT2 `L` record identifier is never used by the landfall detection
algorithm. It is used only afterward as an independent validation reference.

For Florida hurricane-strength landfall records from 1900 onward, the current
detector matches 85 of 90 HURDAT2 reference events (94.4% reference coverage).

Among matched events:

- Median time difference: 9.9 minutes
- Mean time difference: 15.5 minutes
- Median spatial difference: 3.2 km
- Mean spatial difference: 4.7 km

The remaining unmatched reference events are concentrated around the Florida
Keys and Dry Tortugas, where rounded historical HURDAT2 coordinates and the
modern Census boundary do not always produce the same literal coastline
intersection.

Validation also helped identify and remove two interstate crossings that were
initially classified as Florida entries. These were land-to-land crossings
from Alabama rather than true water-to-land landfalls.

The detector is intentionally not adjusted to force agreement with the `L`
records, since those records are used only as an external validation signal.
