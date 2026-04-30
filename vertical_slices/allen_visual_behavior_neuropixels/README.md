# Allen Visual Behavior Neuropixels Slice

This vertical slice maps a single Allen Visual Behavior Neuropixels NWB trials
table into the behavtaskatlas canonical trial schema. It is behavior-first:
the adapter uses the active change-detection trials table and records VBN
dataset provenance, while deferring spike, LFP, probe, optotagging, video, and
passive-replay joins.

## Scope

- Family: `family.visual-change-detection`
- Protocol record: `protocol.mouse-visual-change-detection-allen`
- Dataset record: `dataset.allen-visual-behavior-neuropixels`
- Source archive: DANDI:000713 version `0.240702.1725`
- Recommended access: AllenSDK `VisualBehaviorNeuropixelsProjectCache`
- Adapter: `src/behavtaskatlas/allen.py`
- Tests: `tests/test_allen.py`

## Workflow

Download or otherwise place one VBN NWB file locally, then run:

```bash
uv sync --extra allen
uv run --extra allen behavtaskatlas allen-vbn-download \
  --nwb-url https://visual-behavior-neuropixels-data.s3.us-west-2.amazonaws.com/<key>.nwb \
  --out-file data/raw/allen_visual_behavior_neuropixels/session.nwb
uv run --extra allen behavtaskatlas allen-vbn-harmonize \
  --nwb-file data/raw/allen_visual_behavior_neuropixels/session.nwb
uv run behavtaskatlas allen-vbn-analyze
uv run behavtaskatlas allen-vbn-report
uv run behavtaskatlas site-index
```

The generated artifacts are ignored by git under
`derived/allen_visual_behavior_neuropixels/`.

## Canonical Decisions

VBN uses the same operational go/no-go change-detection task as the Allen
Visual Behavior 2P slice. The adapter therefore reuses the Allen
change-detection harmonizer and changes the dataset identity, provenance, and
caveats rather than duplicating parsing logic.

The slice preserves image identities, image-pair labels, lick counts, reward
volume, aborted trials, and auto-reward flags. It reports hit rate,
false-alarm rate, d-prime, per-image-pair hit rate, and hit lick latency.

## Deferred Joins

The VBN archive is much richer than the behavior slice: ecephys sessions,
probe/channel/unit tables, LFP, passive replay, receptive-field mapping,
optotagging, raw videos, and stimulus-presentation alignment are all outside
the current MVP slice. Those should be added as explicit neural and video
extensions rather than hidden inside the behavioral adapter.
