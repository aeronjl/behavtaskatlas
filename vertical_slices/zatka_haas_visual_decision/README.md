# Zatka-Haas Visual Decision Slice

This slice now has a behavior-first report from the public higher-power
optogenetic inactivation table. The full Figshare archive is split across 19.6
GB, but the split ZIP central directory is available from the tail of part
`.004`; that made it possible to locate and range-download only
`OptogeneticInactivation/Inactivation_HigherPower.mat` from part `.001`.

The adapter decodes the MATLAB v7.3/HDF5 table variable `D`, including
categorical `laserRegion` references, and harmonizes 10,054 processed trials.
It maps source `response` codes 1/2/3 to left/right/withhold, treats finite
zero feedback as incorrect for the 1/0 higher-power source coding, and keeps
laser variables in `task_variables`.

The report now includes signed-contrast summaries split by laser state and by
laser region, plus matched perturbation deltas against non-laser trials at the
same signed contrast. The higher-power table contributes 5,257 non-laser trials
and 4,797 laser trials to the family comparison.

The first perturbation-depth pass generates 156 region-by-contrast delta rows
and 12 compact region-effect rows covering left/right VIS, M2, S1, RSP, M1,
and front-outside control targets. Next step: add coordinate-aware maps or
paper-matched causal model fits on top of these descriptive comparisons.
