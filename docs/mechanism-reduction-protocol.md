# Frozen mechanism-reduction protocol

This is a finite-distribution study of public ciphertext statistics, true
decoding margin, and failure in the toy ML-KEM model. It is not an attack or a
claim about production ML-KEM.

Only E0 determines orientations, the optional two-scalar coefficient, and
frozen numerical tail thresholds. E1a, `n4q29d43`, and `n4q19d43` are
evaluation-only. The study uses the existing parameter points, the existing
128 sampled keys with seed `20260913`, and exact inner enumeration.

## Predeclared public statistics

For each centered decompressed coefficient, `x=center(D_du(u))/q` and
`y=center(D_dv(v))/q`. The candidates are `u`, `v`, and stated sums/maxima of:

- first absolute moments;
- second moments;
- extreme frequencies at `|x| >= 1/4` and `|x| >= 3/8`;
- collision concentrations `sum_j p(j)^2`;
- quantizer-boundary mean distances and low-distance frequencies at `1/4`
  and `3/8`.

For compression width `d`, let `L=2^d`, `r=D_d(z)`, and regard the two ideal
continuous compression-cell boundaries adjacent to symbol `z` as
`q(z-1/2)/L` and `q(z+1/2)/L`, with the natural periodic interpretation. The
dimensionless distance, normalized by cell width `q/L`, is

```
b_d(z) = min(|2 L r - q(2z-1)|, |2 L r - q(2z+1)|) / (2q).
```

If this is constant over a symbol alphabet, all derived boundary statistics
are reported as degenerate. No replacement definition is introduced.

For reporting only, the "best simple scalar" is the primary (non-baseline,
non-combination) candidate maximizing the smaller of its two n=4 AUCs, with
lexicographic name as a deterministic tie break. This comparison does not
change the statistic or its orientation.

`T_marg` is loaded unchanged from the previous frozen-score artifact. For every
candidate, E0 fixes sign `+1` when its raw weighted AUC is at least `1/2`, and
`-1` otherwise. Ties fix `+1`. Evaluation never changes the sign.

The optional predeclared two-scalar statistic is
`S_C = S_2sum + lambda E_sum(1/4)`. E0 alone chooses `lambda=b2/b1`, where
`b0+b1*S_2sum+b2*E_sum(1/4)` is the exact-weight least-squares projection of
the failure indicator. If `b1=0`, `lambda=0`. This statistic remains secondary.

## Metrics

- Weighted AUC uses the exact Mann-Whitney definition with half credit for
  ties.
- Retained ranking is `(AUC(S)-1/2)/(AUC(T_marg)-1/2)` when the denominator is
  nonzero.
- Every attainable inclusive upper tail is reported at its actual cost
  `-log2(P[S>=tau])`.
- E0 also freezes thresholds nearest actual tail probabilities `2^-s` for
  `s in {2,4,6,8,10}` using absolute probability distance and a
  higher-threshold tie break. These literal predicates are used for bootstrap
  tail diagnostics.
- Weighted score quintiles use weighted score-mass midpoints and never split a
  tie.
- Weighted rank association is the weighted Pearson correlation of the
  mid-distribution transforms of oriented score and margin. Thus a negative
  value means larger failure-oriented public score accompanies smaller margin.

For n=4, 10,000 paired cluster-bootstrap replicates resample complete outer
keys with replacement using seed `20260915`. Inner executions are never
resampled. Intervals are percentile 95% intervals. For every frozen tail, a
replicate selecting zero mass is counted rather than discarded silently. A
tail is labeled `unsupported` when at least 5% of replicates have zero support;
otherwise its interval uses the valid replicates and reports all counts.

The final decision rule calls a ranking fraction "most" when it is at least
`0.75` at both n=4 points. Case A additionally requires both n=4 AUC lower
confidence limits above `0.5` and negative score-margin rank association. Case
B applies the same rule to the predeclared `S_C` only when Case A fails. All
other outcomes are Case C.
