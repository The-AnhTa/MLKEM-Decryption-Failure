# Frozen-feature propagation milestone

All feature definitions were frozen before E1a was inspected. Values below use randomized boundary-cell selection at exactly `p=2^-10`.

| Family | Feature | E0 Dinf | E0 G(10) | E1a Dinf | E1a G(10) |
|---|---|---:|---:|---:|---:|
| public | at_norm_pair | 2.018000 | 1.885939 | 2.711585 | 2.512145 |
| public | at_pair_histogram | 2.018000 | 1.885939 | 2.711585 | 2.617498 |
| public | at_correlations | 1.853175 | 1.808897 | 2.638724 | 2.534809 |
| public | at_projections | 2.018000 | 1.721214 | 2.638724 | 2.484923 |
| ciphertext | hist_u | 1.310288 | 1.310288 | 1.448923 | 1.448923 |
| ciphertext | hist_v | 1.413323 | 1.413323 | 0.966469 | 0.966469 |
| ciphertext | extreme_symbols | 3.533818 | 3.335108 | 3.410653 | 2.964467 |
| ciphertext | entropy_1024 | 0.502850 | 0.502850 | 0.422112 | 0.422112 |
| ciphertext | decompressed_norms | 3.459223 | 3.430917 | 4.233072 | 4.059620 |
| ciphertext | joint_uv_histogram | 3.533818 | 3.450722 | 4.364557 | 4.200380 |

## Conditional independence given public key

Exact `Dinf(pk) = 2.018000` bits; conditional-independent `Dinf(pk) = 2.024003` bits. Cross-coordinate dependence therefore does not explain the E0 weak-key concentration.

## E2-E5 support certificates

| Preset | Noise bound | Decoding margin | Failure possible? |
|---|---:|---:|---:|
| e2 | 154 | 832 | no |
| e3 | 154 | 832 | no |
| e4 | 190 | 832 | no |
| e5 | 137 | 832 | no |

The E2-E5 toy configurations cannot answer a post-selection question because their failure event has empty support. The next parameter ladder must scale noise with `q` or choose compression/dimensions that retain nonzero failure support.
