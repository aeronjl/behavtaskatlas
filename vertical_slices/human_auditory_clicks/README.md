# Human Auditory Clicks DBS Slice

This slice ingests the Mendeley Data `Poisson Clicks Task, DBS OFF/ON`
MATLAB file and maps it onto the atlas canonical two-choice trial schema.

- Protocol record: `protocol.human-auditory-clicks-button`
- Dataset record: `dataset.london-human-poisson-clicks-dbs-mendeley`
- Source DOI: `10.17632/3j86m7mjx2.1`
- Source file: `poisson_clicks_rawdata.mat`
- Source file SHA-256: `1040c8fe110e8eec206fb589f30dbff681429de4bb64162a116fdec17904d49a`

The source `cdiff` field is left-minus-right clicks at response. The atlas
canonical axis is right-minus-left clicks, matching the rat clicks slice.
The source stores full scheduled click trains; the evidence-kernel analysis
uses only click times up to `rt`, while preserving full scheduled click times
under `task_variables`.

## Commands

```bash
uv sync --extra clicks
uv run --extra clicks behavtaskatlas human-clicks-download
uv run --extra clicks behavtaskatlas human-clicks-harmonize
uv run --extra clicks behavtaskatlas human-clicks-analyze
uv run --extra clicks behavtaskatlas human-clicks-report
```

Generated artifacts are written under ignored
`derived/human_auditory_clicks/london-dbs-poisson-clicks-mendeley/`.

## First Run

The first local run wrote 5,085 canonical trials, 303 psychometric summary
rows, 2 DBS prior contexts, and 10 evidence-kernel bins. No trials were
excluded from the evidence kernel because every trial has a left/right
response, response time, and click-time vectors.
