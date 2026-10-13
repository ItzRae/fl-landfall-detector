
# U.S. Coastal Hurricane Landfalls

An application for analyzing Atlantic HURDAT2 best-track data to identify
hurricane-strength coastal entries across 18 Atlantic and Gulf coastal states
from 1900 onward using independent geometry-based detection. Florida remains
the default dashboard selection.

For each qualifying landfall, the application reports:
- State
- Storm name
- Landfall date and estimated UTC time
- Estimated maximum sustained wind speed at landfall
- Optional landfall coordinates

## Setup

### Running the application

A deployed version of the application is available here:

https://fl-landfall-detector.streamlit.app/

The interface provides:

- State, year, storm, and minimum-wind filters
- Summary metrics
- Interactive landfall map
- Filterable landfall results table


---

### Running locally

#### 1. Create and activate a virtual environment

Using Python 3.11 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:
```bash
.venv\Scripts\activate
```

#### 2. Install dependencies
```bash
pip install -r requirements.txt
```

#### 3. Run the test suite
```bash
python -m pytest
```

#### 4. Run the landfall analysis

The dashboard calculates landfalls directly from the source files and caches the
results in memory. No CSV generation or upload is required:

```bash
streamlit run app.py
```

To download the current Atlantic HURDAT2 file and the pinned 2025 Census state
boundaries automatically:

```bash
python download_data.py
```

The downloader discovers NOAA's Atlantic download link, validates both inputs,
and activates the new pair only after both succeed. Source URLs and the UTC
download time are recorded in `data/downloads/current.json`. Failed downloads
leave the previous inputs active. Snapshots are retained locally and ignored by
Git; the bundled data is used until the first successful download.

On the next Streamlit rerun (reload the page or change a filter), updated input
files invalidate the analysis cache and populate the dashboard directly. The
dashboard analyzes all supported coastal states and lets you select one or more.
Use **Download filtered results** to export the selected events.

### Weekly hosted updates

`.github/workflows/update-data.yml` runs every Monday at 13:23 UTC
(09:23 EDT / 08:23 EST), independently of whether Streamlit is awake.
It also runs when the workflow is added or updated on `main`, seeding the first
tracked snapshot. You can also run it from **GitHub → Actions → Update hurricane data → Run workflow**.
The workflow runs tests, fetches NOAA's current Atlantic file, compares its bytes,
validates changed data, and runs multistate analysis before publishing. Comparing
content also catches revisions at the same URL. Unchanged data causes no commit.
The Census boundary remains pinned to the bundled 2025 version.

Changed inputs are committed to `data/current/hurdat2.txt` and `source.json`
with source URL, SHA-256 checksum, and update time. Streamlit loads this tracked
snapshot ahead of local downloads and bundled historical inputs. Community Cloud
picks up the repository changes, and the source signature invalidates cached
analysis on the next app rerun. No CSV handoff or keep-awake job is required.

The workflow needs Actions enabled and permission to write repository contents;
branch protection must permit its data commits. Failed validation never publishes
an update. A concurrent push to `main` can reject the data push safely; rerun the
workflow in that case. GitHub may delay scheduled runs and may disable schedules
in public repositories after prolonged inactivity; check the Actions run history.

For a local check using the same publishing path:

```bash
python update_data.py
```

Once `data/current/` exists, it takes priority over `download_data.py` snapshots.
Before that first published snapshot, local downloads or bundled files are used.

CSV output remains optional for exports and independent validation:

```bash
python analyze_landfalls.py
```

This writes `output/florida_hurricane_landfalls.csv` and
`output/validation_summary.csv`, using the same analysis as the dashboard.

## Multistate detection

The dashboard supports Alabama, Connecticut, Delaware, Florida, Georgia,
Louisiana, Maine, Maryland, Massachusetts, Mississippi, New Hampshire,
New Jersey, New York, North Carolina, Rhode Island, South Carolina, Texas,
and Virginia. Results include a state field. Each distinct coastal entry is
retained, including multiple entries by one storm in different states.
Neighboring U.S. land is excluded even when that state is not selected.

The command-line `analyze_landfalls.py` remains the Florida export and
validation workflow. Its reference-match statistics below apply only to
Florida and the bundled dataset, not to all states. Multistate analysis has
synthetic crossing tests and Florida regression checks; it has not yet been
validated state by state against historical reference catalogs.

Census U.S. state boundaries do not include Mexican or Canadian land.
International land-border crossings can therefore be misclassified, and
entries near those borders require review. The geometric model also treats
water outside state land polygons as water without distinguishing the ocean
from bays or inland waterways. Results are reconstructed candidates, with the
same interpolation and coastline-resolution limitations described below.

## Input Data

The analysis uses two main input datasets/files:

**Atlantic HURDAT2 Best Track Data**
Provided by NOAA's National Hurricane Center / Hurricane Research Division.
The bundled snapshot covers 1851–2022; the downloader selects NOAA’s current
Atlantic release. The dataset contains storm-center position, status, maximum sustained wind, and related best-track observations.

**2025 U.S. State Cartographic Boundary — 1:500,000**
Provided by the U.S. Census Bureau.
The Florida, Alabama, and Georgia geometries are loaded from the Census state boundary shapefile and used for geometric landfall detection and interstate-crossing exclusion.


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

#### Landfall

**A Florida landfall in this application is detected when the storm's surface center intersects
with the coastline, according to the National Hurricane Center's definition of landfall.** Consecutive HURDAT2 best-track observations are connected by straight track segments, and a Florida landfall is detected whenever the reconstructed storm-center track transitions from water onto the selected Florida land geometry

HURDAT2 latitude and longitude observations are treated as estimates of the
storm-center position. When a coastline crossing occurs between observations,
the center track is linearly interpolated between the surrounding positions.

The detector samples immediately before and after each boundary crossing to
distinguish water-to-land entries from exits or coastline touches. Crossings
from neighboring-state land in Alabama or Georgia into Florida are excluded,
since those are interstate crossings rather than landfalls.

Each distinct water-to-land crossing is retained as a Florida landfall.

#### Qualifying hurricane landfall

A detected landfall qualifies for the hurricane results when the estimated
**maximum sustained wind at the coastline crossing is at least 64 kt (74 mph)**.

This qualification is applied after the geometric landfall is detected. The
HURDAT2 `L` landfall identifier is not used to determine whether a crossing
occurred or whether it qualifies.

#### Multiple Landfalls
A storm may produce more than one Florida landfall. Each distinct water-to-land entry is treated as a separate event.

#### Landfall time + intensity
**How exactly do we assign hurricane status/wind when the coastline crossing falls between two observations?**
Because HURDAT2 observations are generally spaced several hours apart, the exact coastline crossing often occurs between observations.

The application estimates the crossing time and maximum sustained wind using linear
interpolation along the track segment between the surrounding observations. This assumes
approximately linear storm motion and wind change over that interval.

#### Coastline representation and event granularity
Landfall detection depends on the geographic boundary used to represent Florida. This application uses the U.S. Census Bureau’s 2025 1:500k cartographic state boundary, which is a simplified modern representation of Florida and includes islands and fragmented coastal features. HURDAT2’s L records are independently analyzed historical landfall identifiers rather than outputs from this same boundary model. As a result, the reconstructed number and location of geometric coastline crossings are not expected to correspond one-to-one with the catalogued L records, particularly around complex coastlines such as the Florida Keys.

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
Shared in-memory DataFrame
    ├── Streamlit UI (cached)
    └── Optional CSV export
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

For the bundled 1851–2022 dataset, considering Florida hurricane-strength
landfall records from 1900 onward, the detector matches 85 of 90 HURDAT2 reference events (94.4% reference coverage).

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

### Known limitations and design tradeoffs

- **Track interpolation:** HURDAT2 observations are connected with straight line segments, with landfall time and wind linearly interpolated between observations. This is simple and reproducible but does not reconstruct the storm’s exact path between observations.
- **Coastline representation:** Detection uses a modern Census Florida boundary - historical HURDAT2 coordinates and modern coastline geometry do not always align exactly especially around the Florida Keys and small offshore islands.
- **Event granularity:** The detector retains each distinct water-to-Florida-land crossing. Detailed coastline geometry can therefore produce multiple crossings during a broader storm passage, while HURDAT2 `L` records may represent landfall at a coarser “major coastline” level.
- **Track-start boundary cases:** If a storm’s first recorded observation already lies on or inside Florida, the preceding water-to-land transition cannot be reconstructed from HURDAT2 (this does not affect any qualifying hurricane landfalls in the analyzed dataset).
