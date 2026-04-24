# IBL Visual Decision Slice

This is the first deep vertical slice for `behavtaskatlas`.

## Goal

Connect one schema-complete protocol record to public dataset metadata, source trial fields, a canonical trial representation, and baseline analysis expectations.

## Source Protocol

- Protocol record: `protocol.ibl-visual-decision-v1`
- Dataset record: `dataset.ibl-public-behavior`
- Source data access: IBL ONE/OpenAlyx and ALF `trials` objects

## Source Fields

The first adapter targets the IBL ALF trials table/object. Current primary source documentation indicates these core fields are needed for behavioral summaries:

- `contrastLeft`
- `contrastRight`
- `choice`
- `feedbackType`
- `response_times`
- `stimOn_times`
- `probabilityLeft`

The biased/ephys trial extractors also include fields such as `intervals`, `goCue_times`, `feedback_times`, `rewardVolume`, and `firstMovement_times`; these should be added to the harmonized table when the first real session is downloaded.

## Canonical Mapping

| Canonical field | IBL source |
| --- | --- |
| `stimulus_value` | signed contrast, right positive and left negative |
| `stimulus_side` | finite side among `contrastLeft` and `contrastRight` |
| `evidence_strength` | absolute signed contrast |
| `choice` | `choice`: `1` right, `-1` left, `0` no response |
| `correct` | `feedbackType`: `1` correct, `-1` incorrect |
| `response_time` | `response_times - stimOn_times` |
| `prior_context` | `probabilityLeft` |
| `reward` | `rewardVolume` where available |

## Current Implementation

- Adapter: `src/behavtaskatlas/ibl.py`
- Canonical trial model: `CanonicalTrial`
- Generated schema: `schemas/canonical_trial.schema.json`
- Tests: `tests/test_ibl.py`

## Next Steps

1. Install or document the IBL ONE dependency used for real data access.
2. Select one small public session with `_ibl_trials.table.pqt`.
3. Download or cache only the trial table, not full neural/video data.
4. Convert it to the canonical trial table format.
5. Generate a psychometric summary by signed contrast and block prior.
6. Record source dataset revision, adapter version, and transformation caveats.

## Source Notes

The IBL documentation describes loading trials through ONE with `one.load_object(eid, 'trials', collection='alf')`, and documents psychometric utilities that expect `probabilityLeft`, `contrastLeft`, `contrastRight`, `feedbackType`, `choice`, `response_times`, and `stimOn_times`. The IBL biased/ephys trial extractor documentation describes `_ibl_trials.table.pqt` as containing trial fields including `intervals`, `goCue_times`, `response_times`, `choice`, `stimOn_times`, `contrastLeft`, `contrastRight`, `feedback_times`, `feedbackType`, `rewardVolume`, `probabilityLeft`, and `firstMovement_times`.

