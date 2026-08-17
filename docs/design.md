# Design Notes

This document records implementation decisions, tradeoffs, and changes made
during development for this application

## Data Model
## HURDAT2 Parsing
## Florida Boundary Data
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
    explicit error rather than silently undercounting

## Hurricane Qualification
## Edge Cases
## Validation Findings

### Consolidation Experiment
I initially tried consolidating repeated land entries when a storm re-entered the same Florida polygon component. The idea was to reduce overcounting from small islands and detailed coastline geometry.

During validation, though, I found cases where this rule removed legitimate landfalls. For example, the 1945 storm produced two separate water-to-land crossings only minutes apart on the same component, and both corresponded to HURDAT2 landfall records.

Because of that, I removed the consolidation step rather than keep adding heuristics based on time, distance, or component identity. The final detector keeps each independently detected hurricane-strength water-to-land crossing as a candidate event.

### Reference Comparison

I used HURDAT2 L records only as an independent validation source - they are never referenced by the detection logic.

For Florida hurricane landfalls from 1900 onward:
```text
Reference events: 90
Matched: 85
Reference coverage: 94.4%


Computed candidates: 132
Matched computed candidates: 85


Median time difference: 9.9 minutes
Mean time difference: 15.5 minutes


Median spatial difference: 3.2 km
Mean spatial difference: 4.6 km
```

The five unmatched reference events are concentrated around the Florida Keys / offshore island geography. Three of them use the exact same coordinate `(24.6, -82.9)`, which suggests a systematic difference between the HURDAT2 landfall representation and the modern Census boundary used by the detector.

I chose not to add special-case detection rules just to force agreement with the reference data. The remaining mismatches are documented as a limitation of using a detailed modern coastline to infer historical landfall events.