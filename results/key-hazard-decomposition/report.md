# Key/hazard decomposition

This explanatory analysis used only the three committed datasets and the frozen positive `S_u1` orientation. Coordinate diagnostics were recovered by deterministic replay. The n=8 `(key, S_u1, minimum margin)` law matched cell-for-cell; each n=4 replay matched both committed global `(S_u1, minimum margin)` and committed `(key, minimum margin)` projections exactly.

## Results

| dataset | case | total covariance | within | between | within-centered corr(X,M) | corr(X,L) |
|---|---:|---:|---:|---:|---:|---:|
| n4q29d43 | A | 9.47869e-05 | 7.62502e-05 | 1.85367e-05 | -0.0185388 [-0.0294992, -0.00786425] | 0.00788758 [0.00461199, 0.0113335] |
| n4q19d43 | A | 0.00106018 | 0.00093491 | 0.000125268 | -0.0443444 [-0.0523354, -0.0370324] | 0.0186822 [0.0133653, 0.0244827] |
| n8q29d43 | D | -0.00020413 | -7.34519e-05 | -0.000130678 | 0.00992168 [-0.00275895, 0.022238] | -0.00322911 [-0.0119647, 0.00573416] |

All covariance identities close at floating-point precision. Exact local support values were retained without smoothing or outcome-dependent merging. Dashed and dotted plot curves are diagnostic weighted linear and quadratic fits, not predictors.

## Interpretation

- **n4q29d43: Case A - within-key local mechanism.** Within covariance 7.62502e-05 (95% CI 3.76492e-05 to 0.000117214); between covariance 1.85367e-05 (95% CI 2.9456e-06 to 3.67668e-05); centered local margin correlation -0.0185388 (95% CI -0.0294992 to -0.00786425).
- **n4q19d43: Case A - within-key local mechanism.** Within covariance 0.00093491 (95% CI 0.000743682 to 0.00113858); between covariance 0.000125268 (95% CI 3.30501e-05 to 0.000238617); centered local margin correlation -0.0443444 (95% CI -0.0523354 to -0.0370324).
- **n8q29d43: Case D - no stable association.** Within covariance -7.34519e-05 (95% CI -0.000331369 to 0.000185151); between covariance -0.000130678 (95% CI -0.000407563 to 0.000120341); centered local margin correlation 0.00992168 (95% CI -0.00275895 to 0.022238).

## Local linearity diagnostic

| dataset | outcome | slope | linear R2 | quadratic R2 | improvement |
|---|---|---:|---:|---:|---:|
| n4q29d43 | local failure | 0.00197546 | 0.5695 | 0.7733 | 0.2038 |
| n4q29d43 | coordinate margin | -0.24022 | 0.2632 | 0.3520 | 0.0888 |
| n4q19d43 | local failure | 0.0143848 | 0.6137 | 0.6237 | 0.0100 |
| n4q19d43 | coordinate margin | -0.408768 | 0.5485 | 0.7322 | 0.1837 |
| n8q29d43 | local failure | -0.00218366 | 0.0506 | 0.3325 | 0.2819 |
| n8q29d43 | coordinate margin | 0.143956 | 0.3544 | 0.6259 | 0.2715 |

Both n=4 points have the expected positive local-failure slope and negative margin slope. At n=8 both slopes reverse, the local-failure linear fit is weak, and the key-centered correlation interval includes zero. Thus the directional local relation present at n=4 disappears rather than transferring to n=8.

## Answers

**Why did `S_u1` work at n=4?** At both n=4 points, the signal is primarily a within-key local coordinate effect.

**Why did it fail at n=8?** At n=8, neither covariance decomposition nor the key-centered local relation is stable enough to support the n=4 mechanism.

These are toy-model, algorithmic findings and are not a production ML-KEM security claim.
