# Strict mechanism-reduction study

This is a finite-distribution/statistical study, not a production ML-KEM claim or an attack.

Frozen configuration SHA-256: `4cbd0107c701f65b66745502a01c02c78a4e4ac6a4fac3c0ddaf24f6b1f14395`.

## Q1. Can one transparent scalar explain most of the transferable marginal-score signal?

The predeclared reporting rule selects `S_u1`. It retains 0.947 of T_marg's above-random AUC at n4q29d43 and 1.859 at n4q19d43. Thus the answer is yes under the predeclared 0.75 retained-ranking rule. Bootstrap support and margin tracking are assessed separately below.

## Q2. What is the signal associated with?

Among the predeclared one-dimensional candidates, `S_u1` maximizes the smaller n=4 AUC. This identifies coefficient magnitude, specifically the normalized first absolute moment of u, as the primary association; it is not chiefly a second-moment, extreme-symbol, boundary, or concentration effect. E0-degenerate boundary statistics: B_u_low_1_4, B_v_low_1_4, B_sum_low_1_4, B_v_low_3_8. The AUC table distinguishes magnitude/energy, extremes, boundary geometry, and concentration without refitting. Diagnostic one-variable fits to the frozen marginal weights give u: absolute_value R^2=0.2967; v: squared_value R^2=0.3348.

## Q3. Is the best scalar above random at both n=4 points?

n4q29d43 AUC=0.553478 [0.522106, 0.585270]; n4q19d43 AUC=0.561882 [0.545574, 0.578770].

## Q4. Does it track true decoding margin?

Weighted score-margin rank correlations are -0.064664 and -0.122821; negative means higher failure-oriented score accompanies smaller margin. Mean margin decreases across all five score quintiles at both n=4 points, supporting a systematic shift; the report does not claim full stochastic dominance.

## Q5. How much T_marg ranking is retained?

Retained fractions are 0.947 and 1.859. This ratio is interpreted cautiously because both baseline n=4 AUC excesses are modest.

## Q6. Are rare tails supported by independent outer-key clusters?

There are 20 frozen dataset/statistic/cost operating points with at least 5% zero-support bootstrap replicates. They are labeled unsupported in the tables; zero-mass replicates are never silently discarded. For `S_u1`, costs [2, 4] (q29) and [2, 4] (q19) are supported, while costs [6, 8, 10] and [6, 8, 10] are unsupported, respectively.

## Q7. Simplest plausible mechanism

The simplest supported description is larger public `S_u1=(1/n) sum_i |center(Decompress(u_i))/q|` shifting the true decoding-margin distribution downward, which in turn controls decryption failure. This is an empirical finite-model relationship, not a security attack.

## Decision

**CASE A: SIMPLE-MOMENT REDUCTION.**

Stop classifier experimentation and study P[M <= t | S=s] or tail bounds analytically.

E0 and E1a are exact. n=4 results are 128-key empirical mixtures with exact inner enumeration; intervals resample outer keys only.
