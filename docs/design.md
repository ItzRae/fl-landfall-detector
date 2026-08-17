# Design Notes

This document records implementation decisions, tradeoffs, and changes made
during development for this application

## Data Model

I kept the core models small so each one represents a different stage of the
analysis:

- `Observation` represents a single HURDAT2 track record and stores the timestamp,
storm status, latitude, longitude, maximum sustained wind, and record identifier.
- `Storm` groups the ordered observations for one tropical cyclone
- `TrackEntry` represents a computed water-to-land crossing. It stores the
crossing point, its position along the source track segment, the interpolated
crossing time, and the interpolated wind speed
- `LandfallEvent` adds the storm ID and storm name to a qualifying `TrackEntry`
for reporting and output.

I kept the HURDAT2 record identifier on `Observation` because it is useful for
independent validation but the landfall detector never reads it.

## HURDAT2 Parsing

The parser reads the Atlantic HURDAT2 text file storm by storm - each header
provides the storm ID, name, and number of following observations, which are
then parsed into `Observation` objects.

- Latitude and longitude values are converted into signed decimal coordinates (west and south represented as negative values) 
- HURDAT2 missing-value sentinels such as `-99` are converted to `None` rather than treated as real
measurements.
- Timestamps are built from the date and time fields in each observation. The
original observation order is preserved because consecutive observations are
later used to reconstruct the storm track

The parser does not interpret the `L` record identifier as part of landfall
detection. It is stored only so it can be used later in a separate validation
pipeline to check matches.

## Florida Boundary Data

I used the **2025 Census cartographic state boundary at 1:500,000 scale** and
selected the Florida geometry from the state dataset. 
This means the detector is comparing historical best-track positions against a modern coastline representation which is a source of small spatial disagreement.

The geometry is converted to EPSG:4326 (standard WGS84 geographic coordinate system) 
so it uses the same longitude and latitude coordinate system as HURDAT2. 
Shapely expects coordinates in `(x, y)` order, so storm positions are represented as `(longitude, latitude)`

Florida is represented as a `MultiPolygon`, which is important because the
state boundary includes the mainland as well as the Keys and other offshore
islands. This detail allows the detector to find water-to-land crossings on
separate Florida land components, but it also means the computed results can
be more geographically detailed than the HURDAT2 landfall records.

The same Census state dataset is also used for Alabama and Georgia. Their
combined geometry is passed to the detector so an interstate land crossing is
not mistaken for a water-to-land Florida landfall.



## Landfall Detection

### Entry Policy

middle-of-segment:
    exterior → interior
    = entry

segment endpoint:
    exterior → coastline
    = entry

segment start:
    ignored so a shared coastline observation isn't counted twice

non-point coastline overlap:
    explicit error so it doesn't silently undercount

### Excluding interstate crossings

While I was reviewing unmatched computed events, I found that the original entry rule treated any outside-Florida → inside-Florida transition as a landfall -- that incorrectly included storms entering Florida over land from Alabama.

To distinguish true water-to-land entries from interstate crossings, the detector now checks whether the point immediately before entering Florida is on neighboring-state land. Crossings from Alabama or Georgia into Florida are excluded.

This removed two interstate crossings from the computed results without reducing HURDAT reference coverage.

## Hurricane Qualification

Landfall detection and hurricane qualification are handled as two separate
steps.

First, the geometry logic determines whether the storm center crosses from
water onto Florida land. That crossing is a landfall regardless of intensity.

For the final hurricane-landfall results, the application then checks the
estimated maximum sustained wind at the crossing. A landfall qualifies when the
interpolated wind is at least 64 kt.

Because a coastline crossing usually occurs between HURDAT2 observations, the
crossing time and wind speed are linearly interpolated between the surrounding
records. This assumes approximately linear storm movement and wind change
between those observations.

Note: If the wind value cannot be estimated because one of the surrounding wind
measurements is missing, that crossing is not included in the qualifying
hurricane results.

## Edge Cases

The following cases shaped the final detection policy:

- **Outside → inside:** counted as a normal landfall entry.
- **Inside → outside:** treated as an exit and not reported.
- **Outside → outside without crossing land:** ignored.
- **Outside → land → outside in one track segment:** the entry is still
  detected even though both observations are offshore.
- **Multiple crossings in one segment:** each water-to-land transition is
  retained and processed in track order.
- **Crossing exactly at a segment endpoint:** the preceding segment owns the
  crossing so it is not counted again when the next segment starts from the
  coastline.
- **Track overlapping the coastline:** non-point boundary intersections are
  treated explicitly as unsupported rather than silently guessing.
- **Interstate crossings:** Alabama or Georgia land → Florida land is excluded
  because the storm was already over land.
- **Multiple Florida landfalls:** a storm may leave Florida, move back over
  water, and make another landfall later. Those entries are retained
  separately.
- **Fragmented coastal geometry:** the Keys and other islands can produce
  several literal water-to-land crossings during one broader coastal episode.
  These are kept rather than collapsed with an arbitrary deduplication rule.

## Validation Findings

### Consolidation Experiment
I initially tried consolidating repeated land entries when a storm re-entered the same Florida polygon component. The idea was to reduce overcounting from small islands and detailed coastline geometry.

During validation, though, I found cases where this rule removed legitimate landfalls. For example, the 1945 storm produced two separate water-to-land crossings only minutes apart on the same component, and both corresponded to HURDAT2 landfall records.

Because of that, I removed the consolidation step rather than keep adding heuristics based on time, distance, or component identity. The final detector keeps each independently detected water-to-land crossing as a landfall, then applies the hurricane-strength filter separately for the final results.

### Remaining mismatches

The final detector matches 85 of 90 Florida hurricane-strength HURDAT2
landfall records from 1900 onward.

The remaining misses are concentrated around the Florida Keys and Dry Tortugas. Three reference events share the exact HURDAT2 coordinate `(24.6, -82.9)`, but their reconstructed track segments do not intersect the modern Census Florida geometry.

I treat these as differences between the rounded historical HURDAT2 landfall representation and the modern boundary dataset rather than adding coordinate-specific detection rules.

### Reference Comparison

I used HURDAT2 L records only as an independent validation source - they are never referenced by the detection logic.

For Florida hurricane landfalls from 1900 onward (analysis done in scrap test file):
```text
Reference events: 90
Matched: 85
Reference coverage: 94.4%


Computed qualifying hurricane landfalls: 130
Matched hurrican landfalls: 85


Median time difference: 9.9 minutes
Mean time difference: 15.5 minutes


Median spatial difference: 3.2 km
Mean spatial difference: 4.6 km
```

The five unmatched reference events are concentrated around the Florida Keys / offshore island geography. Three of them use the exact same coordinate `(24.6, -82.9)`, which suggests a systematic difference between the HURDAT2 landfall representation and the modern Census boundary used by the detector.

I chose not to add special-case detection rules just to force agreement with the reference data. The remaining mismatches are documented as a limitation of using a detailed modern coastline to infer historical landfall events.

### Computed-event granularity

The detector keeps each distinct hurricane-strength water-to-land crossing
against the detailed Florida boundary. This can produce several geometric
entries during one broader coastal landfall episode, especially around
fragmented coastline and islands.

While diagnosing the system, 55% of unmatched computed events occurred on track segments
that generated multiple hurricane-strength entries, and 60% occurred within
90 minutes of another computed event that matched a HURDAT2 reference record.

Because legitimate distinct landfalls can also occur close together, I removed the original same-component consolidation rule and chose not to replace it with an arbitrary time-, distance-, or component-based deduplication rule.