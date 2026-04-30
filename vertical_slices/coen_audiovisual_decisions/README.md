# Coen Audiovisual Spatial Wheel Slice

This slice turns the Coen et al. UCL processed release into an adapter-backed workflow for mouse audiovisual spatial decision-making.

## Scope

- Protocol record: `protocol.mouse-audiovisual-spatial-wheel`
- Dataset record: `dataset.coen-audiovisual-decisions-ucl`
- Source: UCL Research Data Repository `BehaviorData.zip` processed release
- Code reference: `pipcoen/2023_CoenSit`
- Local source input: either a MATLAB combined `spatialAnalysis` block or an exported CSV/TSV trial table with the same trial fields

## Operational Mapping

The adapter preserves the source's operational variables instead of collapsing the task into one cognitive label:

- `visDiff`: signed visual evidence, right positive
- `audDiff`: signed auditory evidence, right positive
- `responseCalc`: wheel choice, with `1=left` and `2=right`
- `correctResponse`: source-defined correct side where available
- `reactionTime`: response latency relative to stimulus onset
- `trialType.visual`, `trialType.auditory`, `trialType.coherent`, `trialType.conflict`, `trialType.blank`: modality and cue-congruence flags
- `inactivation.laserType`, `inactivation.galvoPosition`, `inactivation.laserOnsetDelay`: perturbation metadata retained for later causal analyses

The scalar `stimulus_value` is a descriptive rightward evidence proxy (`visDiff + audDiff`) used only for a quick psychometric view. The primary slice outputs are modality, condition, and conflict summaries that keep visual and auditory evidence separate.

## Local Workflow

Download and unzip the UCL data outside version control. The public MATLAB code expects one directory containing per-mouse folders such as `PC011`, plus `XHistology` and `XSupData`.

For a MATLAB combined block export:

```bash
uv run behavtaskatlas coen-harmonize \
  --source-file data/raw/coen_audiovisual_decisions/coen_behavior_export.mat
uv run behavtaskatlas coen-analyze
uv run behavtaskatlas coen-report
uv run behavtaskatlas site-index
```

For a CSV export, pass the exported trial table instead:

```bash
uv run behavtaskatlas coen-harmonize \
  --source-file data/raw/coen_audiovisual_decisions/coen_behavior_export.csv
```

Generated artifacts are written under:

```text
derived/coen_audiovisual_decisions/coen-audiovisual-spatial-wheel-ucl/
```

The source release is large and uses CC BY-NC-ND 4.0, so raw and processed source files remain in ignored local storage.
