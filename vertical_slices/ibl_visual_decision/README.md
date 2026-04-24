# IBL Visual Decision Slice

This is the first deep vertical slice for `behavtaskatlas`.

## Goal

Connect one schema-complete protocol record to public dataset metadata, source trial fields, a canonical trial representation, and baseline analysis expectations.

## Source Protocol

- Protocol record: `protocol.ibl-visual-decision-v1`
- Dataset record: `dataset.ibl-public-behavior`
- Source data access: IBL ONE/OpenAlyx and ALF `_ibl_trials.table.pqt`

## Source Fields

The first adapter targets the IBL ALF trials table. Current primary source documentation indicates these core fields are needed for behavioral summaries:

- `contrastLeft`
- `contrastRight`
- `choice`
- `feedbackType`
- `response_times`
- `stimOn_times`
- `probabilityLeft`

The selected table revision for the first verified session is `2025-03-03` (`_ibl_trials.table.pqt`, dataset id `91928c8f-8278-47d9-bc69-a4805d3924ec`, hash `0c404a34978db3eaad31198f162ae693`). The biased/ephys trial extractors also include fields such as `intervals`, `goCue_times`, `feedback_times`, `rewardVolume`, and `firstMovement_times`; these can be added to the harmonized table when needed.

## Canonical Mapping

| Canonical field | IBL source |
| --- | --- |
| `stimulus_value` | signed contrast, right positive and left negative |
| `stimulus_side` | finite side among `contrastLeft` and `contrastRight` |
| `evidence_strength` | absolute signed contrast |
| `choice` | `choice`: `1` left, `-1` right, `0` no response |
| `correct` | `feedbackType`: `1` correct, `-1` incorrect |
| `response_time` | `response_times - stimOn_times` |
| `prior_context` | `probabilityLeft` |
| `reward` | `rewardVolume` where available |

## Current Implementation

- Adapter: `src/behavtaskatlas/ibl.py`
- Canonical trial model: `CanonicalTrial`
- Generated schema: `schemas/canonical_trial.schema.json`
- Tests: `tests/test_ibl.py`

## Regeneration Command

The default command targets the first selected public session:

```bash
uv sync --extra ibl
uv run behavtaskatlas ibl-harmonize
uv run behavtaskatlas ibl-analyze
uv run behavtaskatlas ibl-report
```

By default this writes ignored local artifacts under:

```text
derived/ibl_visual_decision/ebce500b-c530-47de-8cb1-963c552703ea/
```

The command has been verified against this session and generated:

- 569 canonical trial rows.
- 27 summary rows grouped by signed contrast and prior context.
- Descriptive analysis JSON.
- Dependency-free SVG psychometric plot.
- Static HTML report.
- Fitted four-parameter logistic psychometric estimates per prior block.
- 32 no-response trials.
- 0 missing-stimulus trials.
- 0 missing-response-time trials.
- IBL choice codes are mapped as `1` left and `-1` right.

The selected session metadata is:

- `eid`: `ebce500b-c530-47de-8cb1-963c552703ea`
- subject: `MFD_09`
- lab: `churchlandlab_ucla`
- start time: `2023-10-19T12:54:25.961859`
- task protocol: `_iblrig_tasks_ephysChoiceWorld`
- source URL: `https://openalyx.internationalbrainlab.org/sessions/ebce500b-c530-47de-8cb1-963c552703ea`
- report: `derived/ibl_visual_decision/ebce500b-c530-47de-8cb1-963c552703ea/report.html`

## Next Steps

1. Confirm IBL data licensing and whether derived canonical trial tables can be committed.
2. Tighten handling of IBL dataset revisions in provenance.
3. Add confidence intervals or bootstrap bands around fitted psychometric summaries.
4. Decide whether the report should include response-time summaries once trial table policy is settled.

## Source Notes

The IBL documentation describes loading trials through ONE and documents psychometric utilities that expect `probabilityLeft`, `contrastLeft`, `contrastRight`, `feedbackType`, `choice`, `response_times`, and `stimOn_times`. The IBL biased/ephys trial extractor documentation describes `_ibl_trials.table.pqt` as containing trial fields including `intervals`, `goCue_times`, `response_times`, `choice`, `stimOn_times`, `contrastLeft`, `contrastRight`, `feedback_times`, `feedbackType`, `rewardVolume`, `probabilityLeft`, and `firstMovement_times`.
