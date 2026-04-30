# Odoemene Visual Evidence Accumulation Slice

This slice turns the Odoemene et al. CSHL dataset into an adapter-backed workflow for visual pulse-train evidence accumulation.

## Source Protocol

- Protocol record: `protocol.mouse-visual-flash-rate-accumulation`
- Dataset record: `dataset.odoemene-visual-evidence-accumulation-cshl`
- Dataset DOI: `10.14224/1.38944`
- CSHL record: <https://repository.cshl.edu/id/eprint/38944/>
- Metadata PDF: <https://repository.cshl.edu/38944/3/DataDescription_Odeomene2020.pdf>

## Source Fields

The CSHL metadata describes a MATLAB file of about 137 MB containing a `1 x 29` subject structure array. Each subject has raw choice data concatenated across sessions:

- `stimEventList`: per-trial stimulus event indicators in 25 bins of 40 ms.
- `stimRate`: overall flash rate for the 1 s stimulus.
- `subjectResponse`: `1` low-rate response, `2` high-rate response.
- `correctResponse`: correct low-rate or high-rate category, using the same coding.
- `validTrial`: whether the subject gave a valid response.
- `success`: whether the subject response matched the correct response.
- `waitTime`: center-port sampling time.
- `moveTime`: time from center-port withdrawal to side-port response.
- `sessionID`: source session identifier.
- `numSessions`: total sessions concatenated for that subject.

## Current Interpretation

The adapter maps low-rate choices to canonical `left` and high-rate choices to canonical `right`; this is a category convention, not necessarily physical port side. Training contingency is preserved as `prior_context` when the MATLAB subject structure provides it. Invalid trials remain in the canonical table as `choice: no-response`.

## Local Regeneration

After downloading the CSHL MATLAB file into ignored local storage:

```bash
uv run behavtaskatlas odoemene-harmonize \
  --mat-file data/raw/odoemene_visual_accumulation/Odoemene2020.mat
uv run behavtaskatlas odoemene-analyze
uv run behavtaskatlas odoemene-report
uv run behavtaskatlas site-index
```

Generated artifacts are written under:

```text
derived/odoemene_visual_accumulation/odoemene-visual-evidence-cshl/
```

For the current public artifact release, Odoemene is explicitly treated as an
adapter-ready follow-up slice. The protocol, dataset, and adapter contract stay
visible in the atlas, but missing local report artifacts should warn rather
than block publication until the CSHL MATLAB file is available locally.

The analysis emits both a signed-rate psychometric summary and a descriptive 25-bin event-choice kernel. The kernel is deliberately descriptive; fitting a full psychophysical GLM is deferred.
