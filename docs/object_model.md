# Object Model

The MVP separates four levels that are often conflated in prose descriptions of behavioral tasks.

## Task Family

A task family captures the reusable operational idea, such as visual 2AFC contrast discrimination or auditory click evidence accumulation. Families group protocols but should not imply that all grouped protocols are interchangeable.

## Protocol

A protocol is the primary curation unit. It describes one concrete task variant with explicit species, stimulus, choice structure, timing, feedback, training, apparatus, software, references, and provenance.

## Dataset

A dataset record links one or more protocols to public or private data sources. Raw data should generally remain in source archives. The atlas records access details, licensing status, expected trial-table mappings, caveats, and later harmonized derivative artifacts.

Dataset records also declare `source_data_level`, because not every useful
slice is equally close to raw behavior. The current controlled levels are
`raw-trial`, `processed-trial`, `processed-session`, `figure-source-data`, and
`aggregate-only`.

## Vertical Slice

A vertical slice links one protocol and one dataset to local reproducible
artifacts: harmonized rows, analysis outputs, plots, reports, and provenance.
Each slice carries comparison metadata and repeats the `source_data_level`
actually used by the slice. This lets the static atlas show report availability
and source strength side by side.

## Implementation

An implementation record describes task-control code or a reference implementation. The atlas distinguishes code actually used for a dataset from simplified reference implementations.

## Analysis Result

Analysis result records will be added after the first data harmonization pass. They should be generated from versioned scripts wherever possible and should record source dataset versions, adapter versions, parameters, and outputs.

## Design Rule

Operational variables come first. Cognitive interpretations are allowed only as sourced claims with confidence and caveats.
