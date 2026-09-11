# ML-KEM Decryption Failure Under Post-Selection

## Problem

ML-KEM's published decapsulation-failure probability is an average over key generation and honest encapsulation. This does not determine the failure probability after an adversary selects keys or executions using observable information.

Ignoring representation details, ML-KEM decryption recovers

$$
w=\mu(m)+N,
$$

where the effective noise is

$$
N=e^T y-s^T e_1+e_2-s^T c_u+c_v.
$$

Here $c_u$ and $c_v$ are deterministic compression errors. The coefficients of $N$ are dependent because negacyclic multiplication reuses input coefficients and compression couples its errors to the values being compressed. Any analysis must preserve these dependencies.

Let $F$ be the event that some coefficient crosses its decoding boundary, and let

$$
\delta_{\mathrm{avg}}=\Pr[F].
$$

For an efficiently computable predicate $P$ on observable data (such as a public key, ciphertext, transcript, or specified leakage), define

$$
\delta_P=\Pr[F\mid P=1].
$$

If $p=\Pr[P=1]$, probability theory alone gives the tight bound

$$
\delta_P\le \min\!\left(1,\frac{\delta_{\mathrm{avg}}}{p}\right).
$$

Thus a tiny average failure probability does not, by itself, rule out efficiently recognizable subsets on which failures are much more likely. The central question is:

> How stable is ML-KEM's decryption-failure probability under computationally accessible post-selection?

A useful correctness profile is

$$
\delta_{\mathrm{cond}}(p)=
\sup_{\substack{P\in\mathrm{PPT}\\\Pr[P=1]\ge p}}
\Pr[F\mid P=1].
$$

The research goal is either to prove an ML-KEM-specific bound substantially stronger than $\delta_{\mathrm{avg}}/p$, without assuming coefficient independence, or to exhibit an efficient predicate that significantly amplifies failure probability at an operationally attainable selection rate.

Key-only predicates $P(pk)$ and execution-level predicates $P(pk,c)$ should be treated separately: a rare weak-key condition can be reused across many encapsulations, whereas a ciphertext condition generally incurs its selection cost on every execution. Leakage must also be defined structurally or statistically; a bit-count bound alone is insufficient because one leaked bit could encode $F$ itself. Faults require a separate interventional model rather than ordinary conditioning.

Any claimed amplification should report three quantities:

$$
\Pr[P=1],\qquad
\frac{\Pr[F\mid P=1]}{\delta_{\mathrm{avg}}},\qquad
\operatorname{Cost}(P).
$$

At full ML-KEM parameters, ordinary Monte Carlo cannot resolve probabilities near $2^{-139}$ or smaller. Rigorous evaluation therefore requires exact analysis, certified tail bounds, or importance sampling with controlled likelihood ratios.
