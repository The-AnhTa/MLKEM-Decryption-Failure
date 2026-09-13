# Frozen normalized ciphertext-score transfer protocol

This study tests statistical dependence in the finite toy ML-KEM model. It
does not make a claim about production ML-KEM security.

## Discovery and evaluation boundary

Only the exact E0 distribution may determine score parameters. E1a,
`n4q29d43`, and `n4q19d43` are evaluation-only distributions. The evaluator
loads a frozen E0 artifact and cannot refit or reverse a score.

The study uses the following immutable choices:

- centered normalized decompressed coordinates are binned into
  `[-1/2,-1/4)`, `[-1/4,0)`, `[0,1/4)`, and `[1/4,1/2)`;
- bin assignment is performed by exact integer comparisons, not floating
  point comparisons;
- joint histograms are ordered row-major by the `u` bin and then the `v` bin;
- histogram counts are divided by `n`, so each histogram has unit mass;
- score weights use the natural logarithm and `epsilon = 2^-40`;
- E0 score weights are serialized both as decimal binary64 values and with
  Python's exact hexadecimal binary64 representation;
- selection costs are `s = 2, 4, 6, 8, 10`;
- among observed score thresholds, calibration chooses the threshold whose
  inclusive upper-tail mass is closest in absolute probability to `2^-s`;
  ties choose the larger threshold;
- weighted ROC AUC gives half credit to tied positive/negative scores;
- margin diagnostics use five weighted score quantiles and never split a
  score tie;
- sampled-key uncertainty uses 10,000 paired cluster-bootstrap replicates,
  resampling complete outer keys with replacement, seed `20260914`, and
  percentile 95% intervals.

If a predicate selects zero probability mass, its conditional failure
probability, amplification, and gain are undefined. They must not be reported
as zero. Exact distributions use degenerate confidence intervals equal to the
reported statistic; sampled-key distributions use cluster-bootstrap intervals.

## Scores

For a ciphertext coefficient, let

```
x_i = center(Decompress_du(u_i)) / q
y_i = center(Decompress_dv(v_i)) / q.
```

For the fixed 4 by 4 grid, `H_ab` is the fraction of coefficient positions in
joint bin `(a,b)`. E0 determines

```
P_b      = E[H_b]
P_b_fail = E[H_b | F]
w_b      = log((P_b_fail + epsilon) / (P_b + epsilon)).
```

The frozen joint score is `sum_b w_b H_b`. Marginal `u` and `v` weights are
learned by the same E0-only rule, and the marginal score is the sum of the two
marginal scores. Logarithm base affects score scale only; reported amplification
gain always uses `log2`.

## Dataset manifest

| Dataset | Role | Enumeration |
|---|---|---|
| E0 | discovery and exact evaluation | global exact ciphertext DP |
| E1a | evaluation only | global exact ciphertext DP |
| n4q29d43 | evaluation only | 128 sampled keys, seed 20260913; exact inner randomness |
| n4q19d43 | evaluation only | 128 sampled keys, seed 20260913; exact inner randomness |

An optional n=8 evaluation may run only after all required outputs are complete,
and must consume the same frozen artifact without modification.
