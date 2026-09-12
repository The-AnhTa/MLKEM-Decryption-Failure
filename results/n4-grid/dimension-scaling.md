# Predicate transfer and n=4 dimension scaling

The E0 model and n=4 grid protocol were committed before target evaluation. No feature family was added after target results were inspected.

## E0-trained predicates evaluated on exact E1a

Nominal E0 budget is `2^-10`; achieved target mass is reported because the predicate is unchanged.

| Feature | Randomized achieved p | Randomized A | Oracle retained | Deterministic achieved p | Deterministic A |
|---|---:|---:|---:|---:|---:|
| at_norm_pair | 0.00416955 | 2.1435 | 0.826 | 0.00554017 | 2.1435 |
| extreme_symbols | 0.000782497 | 7.9921 | 1.000 | 0.000205233 | 10.6343 |
| decompressed_norms | 0.00154725 | 10.7194 | 0.960 | 0.00167145 | 10.7204 |
| joint_uv_histogram | 0.000781939 | 15.4159 | 0.830 | 0.000765116 | 15.3019 |

The E0 predicate therefore transfers across `q=17 -> 19`; this is predicate transfer, not an E1a-refitted frontier.

## Selected n=4 points

| Preset | Mean failure | Approximate 95% mean interval | Rigorous Hoeffding interval |
|---|---:|---:|---:|
| n4q29d43 | 0.005610 | [0.004409, 0.006810] | [0.000000, 0.125650] |
| n4q19d43 | 0.050545 | [0.043878, 0.057212] | [0.000000, 0.170586] |

Intervals are over sampled keys; encapsulation probabilities within each key are exact. The normal interval is approximate, while Hoeffding is distribution-free but very conservative.

## Frozen-feature concentration in sampled n=4 mixtures

These are descriptive empirical-mixture frontiers, not population bounds.

| Preset | Feature | Sample Dinf | Sample G(10) |
|---|---|---:|---:|
| n4q29d43 | at_norm_pair | 2.578822 | 2.578822 |
| n4q29d43 | hist_u | 5.062794 | 3.650396 |
| n4q29d43 | extreme_symbols | 2.799759 | 2.243590 |
| n4q29d43 | decompressed_norms | 7.477831 | 5.163708 |
| n4q29d43 | joint_uv_histogram | 7.477831 | 7.477831 |
| n4q19d43 | at_norm_pair | 1.566163 | 1.566163 |
| n4q19d43 | hist_u | 3.113632 | 1.758662 |
| n4q19d43 | extreme_symbols | 1.565339 | 0.418326 |
| n4q19d43 | decompressed_norms | 4.132794 | 2.589528 |
| n4q19d43 | joint_uv_histogram | 4.306277 | 4.237231 |

## E0 predicate applied unchanged at n=4

| Preset | Feature | Achieved p at nominal 2^-10 | Amplification | Oracle retained |
|---|---|---:|---:|---:|
| n4q29d43 | at_norm_pair | 0 | 0.0000 | N/A |
| n4q29d43 | extreme_symbols | 0 | 0.0000 | N/A |
| n4q29d43 | decompressed_norms | 3.30692e-05 | 0.4518 | 0.287 |
| n4q29d43 | joint_uv_histogram | 0 | 0.0000 | N/A |
| n4q19d43 | at_norm_pair | 0 | 0.0000 | N/A |
| n4q19d43 | extreme_symbols | 0 | 0.0000 | N/A |
| n4q19d43 | decompressed_norms | 1.66874e-06 | 8.3753 | 0.935 |
| n4q19d43 | joint_uv_histogram | 0 | 0.0000 | N/A |

## Interpretation

Observable post-selection remains strong in both sampled n=4 mixtures: the joint histogram has sample `G(10)` of about 7.48 and 4.24 bits, respectively. This establishes nonzero-failure dimension-scaling examples, but the values are descriptive for the 128-key mixtures.

The specific E0 `2^-10` predicates do not generally transfer to n=4: most select no target cells, and the decompressed-norm predicate has only tiny support. Thus the experiment supports feature-family survival with dimension, but does not yet establish a dimension-independent predicate. Public-feature `Dinf` values also largely reflect selection among only 128 sampled keys and must not be read as population bounds.
