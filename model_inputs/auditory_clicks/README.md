# Auditory Clicks Model Inputs

`trials_compact.npz` is a compact, tracked cache of the Brunton auditory
click trial features needed for click-model forward evaluation in clean
CI checkouts. The full harmonized `derived/auditory_clicks/trials.csv`
remains an ignored generated artifact and is published in release bundles.

Regenerate the cache from the full derived trials table with:

```sh
uv run python scripts/build_click_model_input.py
```

The cache stores subject labels, signed click-count differences, choices,
stimulus durations, and ragged right/left click-time arrays. It does not
replace the published trial CSV; it only keeps the model audit reproducible
when ignored artifacts are absent.
