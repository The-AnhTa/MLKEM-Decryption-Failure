# Predicate-transfer and dimension-scaling protocol

This protocol was fixed before evaluating the E0-trained model on E1a and
before running the n=4 grid. No additional feature families will be introduced.

## E0 to E1a predicate transfer

`python/predicate_transfer.py train` learns exact likelihood-ratio scores from
E0 only. Its output is a frozen model, not an E1a-refitted frontier. The model
contains predicates for budgets `2^-1` through `2^-20` and fixes both:

- a randomized boundary-cell predicate; and
- the nearer-mass deterministic predicate obtained by including or excluding
  the complete boundary score class.

Raw norm statistics are made dimensionless before scoring. Squared norms are
divided by their coefficient count times `q^2` and assigned to fixed bins of
width `1/32`. Histogram and extreme-symbol counts are represented as exact
frequencies, entropy remains in its pre-existing `1/1024`-bit units, and the
joint symbol histogram is represented by its complete frequency vector.
Feature cells absent from E0 are rejected. Evaluation reports the achieved E1a
selection mass, not merely the nominal E0 budget, and compares against the E1a
oracle at that achieved mass.

## Predeclared n=4 grid

All points use `n=4`, `k=1`, and `eta1=eta2=1`. The grid is the Cartesian
product

```text
q in {17, 19, 23, 29}
(du,dv) in {(3,2), (4,2), (4,3)}
```

The named presets are `n4q{q}d{du}{dv}`. Each point is processed as follows:

1. Reject it if the deterministic support bound proves failure impossible.
2. Otherwise run 12 sampled outer keys with seed `20260912`, enumerating all
   encapsulation randomness exactly. The screening output contains only the
   global and per-key failure laws; feature-conditioned output is suppressed.
3. A point is eligible when its pilot mean failure probability lies in
   `[10^-3,10^-1]`.
4. Select at most two distinct eligible points: the closest in absolute
   log-probability to `0.01`, then the closest remaining point to `0.05`.
   Ties are resolved lexicographically by preset name.
5. For each selected point, run 128 fresh sampled keys with seed `20260913`.
   Public and ciphertext runs use the same sampled keys and enumerate all
   encapsulation randomness exactly.

The final sampled analysis must label sample maxima and sample `D_infinity` as
descriptive, never as population bounds. The primary dimension-scaling claim
uses a predeclared 64/64 key split: the first half constructs predicates within
each frozen feature family, and the second half evaluates them. Confidence
intervals are computed across held-out keys. The complete-sample empirical
frontiers remain secondary descriptive summaries.
