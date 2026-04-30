# IBL Brainwide Map Behavior Slice

This slice reuses the IBL visual-decision behavioral adapter for one Neuropixels
Brainwide Map session while preserving Brainwide Map-specific provenance.

## Scope

- Protocol record: `protocol.ibl-visual-decision-v1`
- Dataset record: `dataset.ibl-brainwide-map-2025`
- Source: IBL Brainwide Map on AWS / OpenAlyx
- ONE project: `ibl_neuropixel_brainwide_01`
- Release tag: `Brainwidemap`
- Default EID: `ebce500b-c530-47de-8cb1-963c552703ea`

## Operational Mapping

The behavior table follows the standard IBL ALF trials table:

- `contrastLeft`, `contrastRight`: signed visual evidence, with rightward
  evidence positive in canonical rows
- `choice`: wheel choice, with `1=left`, `-1=right`, and `0=no-response`
- `feedbackType`: correctness and reward/error feedback
- `stimOn_times`, `response_times`: response latency relative to stimulus onset
- `probabilityLeft`: block prior context for psychometric summaries
- `rewardVolume`: reward amount where available

The current MVP slice is behavior-first. Probe insertions, units, atlas
regions, spike sorting, histology, and video pose fields stay out of the base
canonical trial table until a neural companion table is added.

## Local Workflow

```bash
uv run --extra ibl behavtaskatlas ibl-brainwide-harmonize \
  --cache-dir data/raw/openalyx-cache
uv run behavtaskatlas ibl-brainwide-analyze
uv run behavtaskatlas ibl-brainwide-report
uv run behavtaskatlas site-index
```

Generated artifacts are written under:

```text
derived/ibl_brainwide_map/ebce500b-c530-47de-8cb1-963c552703ea/
```

Use `--eid` to select a different Brainwide Map session, and keep downloaded
ONE/AWS artifacts in ignored local storage.
