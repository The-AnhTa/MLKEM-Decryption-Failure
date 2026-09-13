# Preregistered final frozen-Su1 confirmation protocol

This is a confirmatory finite-distribution experiment, not a feature search, an
attack, or a claim about production ML-KEM. The only public statistic is

```text
S_u1 = sum_i |center(Decompress_du(u_i))| / (n q).
```

Its orientation is fixed at `+1`, exactly as selected from E0 in the completed
mechanism-reduction study. There is no fitting, alternate statistic, sign
choice, or evaluation-point tuning.

## Deterministic point selection

The ordered candidate sequence is:

1. `n8q29d43 = (n,k,q,eta1,eta2,du,dv)=(8,1,29,1,1,4,3)`;
2. `n8q23d43 = (8,1,23,1,1,4,3)`;
3. `n8q19d43 = (8,1,19,1,1,4,3)`.

Each point uses 128 independently sampled outer keys, four independently
sampled `y` polynomials per key, and exact conditional enumeration of every
`e1`, `e2`, and message outcome. The seed is `20260916`. Bootstrap clusters
are whole keys; the four `y` draws and all exact conditional mass stay within
their key cluster.

The feasibility work count is
`128 * 4 * 3^n`, the number of exact `e1` vectors evaluated after sampling key
and `y`. A candidate is feasible iff this is at most `4,000,000`. It has
failure support iff the deterministic noise-support certificate does not prove
failure impossible. Select the first candidate in the stated order satisfying
both conditions. These rules use neither `S_u1`, margin, AUC, correlation, nor
post-selection output. If the selected experiment observes zero failures, stop
and report the zero-failure result; do not move to another candidate.

Full exact `y x e1` enumeration would require `9^8` states per key and is not
within this fixed feasibility budget. The chosen experiment is therefore an
empirical two-stage mixture with exact conditional `e1,e2,message` laws, not a
globally exact n=8 distribution.

## Frozen analysis

- Weighted AUC uses the exact Mann-Whitney definition with half credit for
  ties. The formal AUC condition is that its two-sided percentile 95% cluster-
  bootstrap interval has lower endpoint greater than `0.5`.
- Margin association is weighted Pearson correlation between the weighted
  mid-distribution ranks of `S_u1` and minimum decoding margin. Confirmation
  requires the entire percentile 95% interval to be negative.
- Weighted quintiles use score-mass midpoints and do not split tied scores.
- Every attainable inclusive upper tail is reported at actual cost
  `-log2(P[S_u1 >= tau])` with gain
  `log2(P[F | S_u1 >= tau] / P[F])`.
- Bootstrap uses 10,000 deterministic whole-key resamples with seed
  `20260918`. A tail is `UNSUPPORTED` iff more than 10% of replicates select
  zero probability mass. Zero-support replicates are counted and never
  silently discarded.

Confirmation succeeds iff both the AUC lower endpoint is above `0.5` and the
margin-rank-correlation upper endpoint is below `0`. Quintiles and tails are
supporting/secondary evidence only.
