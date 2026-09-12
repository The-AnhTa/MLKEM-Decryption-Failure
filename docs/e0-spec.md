# E0 exact experiment specification

E0 uses

\[
(n,k,q,\eta_1,\eta_2,d_u,d_v)=(2,1,17,1,1,3,2).
\]

Polynomials are represented canonically in `0..q-1` and multiplied in
`Z_q[X]/(X^n+1)`. A message is an `n`-bit vector. Bit encoding is
`Decompress_1(bit)`.

For canonical `x` and a `d`-bit symbol `y`, the exact integer operations are

```text
Compress_d(x)   = floor((2^d*x + floor(q/2))/q) mod 2^d
Decompress_d(y) = floor((q*y + 2^(d-1))/2^d)
```

Decryption computes

```text
m'[i] = Compress_1(Decompress_dv(vc[i]) - (s^T Decompress_du(uc))[i])
F     = (m' != m)
```

All CBD support points carry multiplicity

\[
W_\eta(x)=\binom{2\eta}{\eta+x}.
\]

All reported counts are arbitrary-precision integer probability masses.

## Ablation probability laws

- `none`: exact compression and decompression above.
- `no-compression`: transmit the uncompressed ring elements exactly.
- `independent-compression`: replace each compression error by an independent
  draw from the exact error marginal induced by a uniform coefficient in
  `Z_q`; preserve negacyclic multiplication by `s`.
- `independent-output`: retain the key distribution, but draw each output
  coordinate independently from its global one-coordinate honest marginal.
  This is a software sanity check, not a scientifically informative ablation
  for public-key selection and not a K-PKE scheme.
- `conditional-independent-given-pk`: preserve the exact public-key posterior
  and every coordinate marginal `Pr[F_i | pk]`, then replace the joint failure
  law by `1-product_i(1-Pr[F_i | pk])`.
