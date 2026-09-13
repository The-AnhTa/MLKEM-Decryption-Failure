# Key/hazard decomposition protocol

This explanatory study uses only the committed `n4q29d43`, `n4q19d43`, and
`n8q29d43` experiments. It does not select parameters, features, orientations,
or thresholds. `S_u1` retains its frozen positive orientation.

The committed global laws retain only the minimum decoding margin. The recovery
driver deterministically replays the same parameters, keys, seeds, and inner
enumerations and exports `(key, X_i, M_i)` sufficient statistics. Its recovered
`(key, S_u1, min_i M_i)` law must match committed sufficient projections before
analysis proceeds. For n=8 this is a cell-for-cell comparison. For the large n=4
archives, the replay must match both the committed global `(S_u1,min_i M_i)` law
and the committed `(key,min_i M_i)` law. Together these validate the statistic/
margin projection and the frozen outer-key replay without repeatedly parsing the
much larger redundant `(key,U-histogram,V-histogram,min-margin)` archive. Thus
recovery adds a diagnostic projection, not a dataset.

All expectations use the exact/conditional-exact integer weights. A coordinate
law represents a uniformly selected coordinate of an execution (the exported
mass is `n` times execution mass). Local support is left discrete; no bins are
merged. Pooled key-conditioned hazards average `P(L_i=1 | X_i=x,K=k)` with the
original key masses, renormalized over keys having positive support at `x`; the
supporting key mass is reported.

Linear and quadratic fits are weighted least squares on exact support-point
means, weighted by coordinate mass. Reported correlations are weighted Pearson
correlations. The within-key correlation centers both variables by their exact
key means. Uncertainty is a percentile cluster bootstrap of outer keys with
10,000 replicates and seed `20260920`; inner laws are never resampled.

For descriptive classification, a covariance component is *material* when its
absolute value is at least 20% of `|within|+|between|`, and *clear* when its 95%
bootstrap interval excludes zero. A local relation is clear when the centered
`corr(X_i,M_i)` interval excludes zero. Case A requires clear/material within,
a clear local relation, and nonmaterial between. Case B reverses within and
between and requires no clear local relation. Case C requires both covariance
components to be material and at least one to be clear. All other outcomes are
Case D. Dataset-specific prose remains limited to these computed diagnostics.
