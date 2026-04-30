# Steinmetz Visual Decision Slice

This vertical slice turns the catalog-only Steinmetz mouse visual decision
dataset into an adapter-backed local workflow. It targets extracted ALF
sessions from the Figshare/ONE release rather than downloading the full
multi-gigabyte archive during tests or CI.

The current local aggregate report is analysis-backed for all 39 extracted
Steinmetz sessions: 10,050 trials across 10 subjects, including 3,305 source
NoGo choices mapped to canonical withhold. A representative per-session report
for `Cori-2016-12-14-001` remains linked from the slice artifacts.

## Source Protocol

- Protocol record: `protocol.mouse-unforced-visual-contrast-wheel`
- Dataset record: `dataset.steinmetz-visual-decision-figshare`
- Source DOI: `10.6084/m9.figshare.9974357.v3`
- Field dictionary: <https://github.com/nsteinme/steinmetz-et-al-2019/wiki/data-files>

## Source Fields

The adapter reads trial-level `.npy` files named with the ALF convention:

- `trials.visualStim_contrastLeft.npy`: left contrast as a proportion.
- `trials.visualStim_contrastRight.npy`: right contrast as a proportion.
- `trials.response_choice.npy`: `+1` left, `-1` right, `0` NoGo.
- `trials.response_times.npy`: response timestamp in seconds.
- `trials.visualStim_times.npy`: visual-stimulus onset timestamp in seconds.
- `trials.feedbackType.npy`: `+1` reward, `-1` negative feedback.
- Optional fields: `trials.goCue_times.npy`, `trials.feedback_times.npy`, `trials.included.npy`, `trials.repNum.npy`, `trials.intervals.npy`.

## Current Interpretation

The source task is not a strict 2AFC task because NoGo/no-turn outcomes are valid behavioral choices, especially for blank trials. The canonical adapter therefore maps source `response_choice == 0` to `choice: withhold`. Binary movement psychometrics are still emitted for comparison with IBL-style 2AFC slices, but they explicitly exclude withhold trials.

## Local Regeneration

After extracting one Steinmetz session into an ignored local directory containing
`trials.*.npy` files:

```bash
uv run behavtaskatlas steinmetz-harmonize \
  --session-dir data/raw/steinmetz_visual_decision/Cori-2016-12-14-001 \
  --session-id Cori-2016-12-14-001 \
  --subject-id Cori
uv run behavtaskatlas steinmetz-analyze --session-id Cori-2016-12-14-001
uv run behavtaskatlas steinmetz-report --session-id Cori-2016-12-14-001
uv run behavtaskatlas steinmetz-aggregate
uv run behavtaskatlas site-index
```

If the extracted session directory has a real session name, pass it through consistently:

```bash
uv run behavtaskatlas steinmetz-harmonize \
  --session-dir data/raw/steinmetz_visual_decision/<session-dir> \
  --session-id <session-dir>
uv run behavtaskatlas steinmetz-analyze --session-id <session-dir>
uv run behavtaskatlas steinmetz-report --session-id <session-dir>
```

Generated artifacts are written under:

```text
derived/steinmetz_visual_decision/<session-id>/
derived/steinmetz_visual_decision/aggregate/
```

The aggregate command scans generated session directories for `trials.csv` and
emits session-level, subject-level, and signed-contrast summaries over the local
Steinmetz set. Pass repeated `--session-id` flags to restrict the aggregate to a
specific subset.
