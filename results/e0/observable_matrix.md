# E0 observable and ablation matrix

| Mode | Observable | D2 (bits) | Dinf (bits) | max amplification | p(z*) | Pr[F|z*] |
|---|---:|---:|---:|---:|---:|---:|
| none | pk | 0.457177 | 2.018000 | 4.05022 | 16384/1212153856 | 5400/16384 |
| none | ciphertext | 1.739766 | 3.533818 | 11.582 | 310528/1212153856 | 292672/310528 |
| none | pk_ciphertext | 3.497130 | 3.619256 | 12.2887 | 8192/1212153856 | 8192/8192 |
| none | ciphertext_symbols | 1.739571 | 3.533818 | 11.582 | 310528/1212153856 | 292672/310528 |
| none | t_norm2 | 0.251528 | 0.696837 | 1.62095 | 25165824/1212153856 | 3319520/25165824 |
| none | t_histogram | 0.257245 | 0.696837 | 1.62095 | 6291456/1212153856 | 829880/6291456 |
| none | t_autocorrelation | 0.167855 | 0.696837 | 1.62095 | 12582912/1212153856 | 1659760/12582912 |
| none | at_norm_pair | 0.439679 | 2.018000 | 4.05022 | 262144/1212153856 | 86400/262144 |
| none | at_pair_histogram | 0.457177 | 2.018000 | 4.05022 | 32768/1212153856 | 10800/32768 |
| none | at_correlations | 0.291408 | 1.853175 | 3.61295 | 65536/1212153856 | 19268/65536 |
| none | at_projections | 0.264958 | 2.018000 | 4.05022 | 16384/1212153856 | 5400/16384 |
| none | hist_u | 0.551931 | 1.310288 | 2.47991 | 37748736/1212153856 | 7617872/37748736 |
| none | hist_v | 0.753095 | 1.413323 | 2.6635 | 103841792/1212153856 | 22507136/103841792 |
| none | extreme_symbols | 1.046461 | 3.533818 | 11.582 | 310528/1212153856 | 292672/310528 |
| none | entropy_1024 | 0.271075 | 0.502850 | 1.41701 | 556702368/1212153856 | 64193520/556702368 |
| none | decompressed_norms | 1.674101 | 3.459223 | 10.9984 | 680256/1212153856 | 608832/680256 |
| none | joint_uv_histogram | 1.739766 | 3.533818 | 11.582 | 310528/1212153856 | 292672/310528 |
| no-compression | pk | 2.087217 | 2.900464 | 7.46667 | 16384/1212153856 | 224/16384 |
| no-compression | ciphertext | 3.071468 | 8.093109 | 273.067 | 1152/1212153856 | 576/1152 |
| no-compression | pk_ciphertext | 8.925759 | 9.093109 | 546.133 | 2/1212153856 | 2/2 |
| no-compression | ciphertext_symbols | N/A | N/A | N/A | N/A | N/A |
| no-compression | t_norm2 | 0.374108 | 0.415037 | 1.33333 | 25165824/1212153856 | 61440/25165824 |
| no-compression | t_histogram | 0.374108 | 0.415037 | 1.33333 | 6291456/1212153856 | 15360/6291456 |
| no-compression | t_autocorrelation | 0.278573 | 0.415037 | 1.33333 | 12582912/1212153856 | 30720/12582912 |
| no-compression | at_norm_pair | 1.893088 | 2.900464 | 7.46667 | 524288/1212153856 | 7168/524288 |
| no-compression | at_pair_histogram | 2.087217 | 2.900464 | 7.46667 | 32768/1212153856 | 448/32768 |
| no-compression | at_correlations | 1.767678 | 2.900464 | 7.46667 | 65536/1212153856 | 896/65536 |
| no-compression | at_projections | 1.500922 | 2.900464 | 7.46667 | 16384/1212153856 | 224/16384 |
| no-compression | hist_u | N/A | N/A | N/A | N/A | N/A |
| no-compression | hist_v | N/A | N/A | N/A | N/A | N/A |
| no-compression | extreme_symbols | N/A | N/A | N/A | N/A | N/A |
| no-compression | entropy_1024 | N/A | N/A | N/A | N/A | N/A |
| no-compression | decompressed_norms | N/A | N/A | N/A | N/A | N/A |
| no-compression | joint_uv_histogram | N/A | N/A | N/A | N/A | N/A |
| independent-compression | pk | 0.471966 | 1.240310 | 2.36249 | 1368408064/101240302206976 | 180168928/1368408064 |
| independent-compression | ciphertext | N/A | N/A | N/A | N/A | N/A |
| independent-compression | pk_ciphertext | N/A | N/A | N/A | N/A | N/A |
| independent-compression | ciphertext_symbols | N/A | N/A | N/A | N/A | N/A |
| independent-compression | t_norm2 | 0.247279 | 0.329470 | 1.25655 | 2101874786304/101240302206976 | 147190882176/2101874786304 |
| independent-compression | t_histogram | 0.247279 | 0.329470 | 1.25655 | 525468696576/101240302206976 | 36797720544/525468696576 |
| independent-compression | t_autocorrelation | 0.170732 | 0.329470 | 1.25655 | 1050937393152/101240302206976 | 73595441088/1050937393152 |
| independent-compression | at_norm_pair | 0.446494 | 1.213784 | 2.31945 | 43789058048/101240302206976 | 5660369728/43789058048 |
| independent-compression | at_pair_histogram | 0.471966 | 1.240310 | 2.36249 | 2736816128/101240302206976 | 360337856/2736816128 |
| independent-compression | at_correlations | 0.378603 | 1.240310 | 2.36249 | 5473632256/101240302206976 | 720675712/5473632256 |
| independent-compression | at_projections | 0.344367 | 1.240310 | 2.36249 | 1368408064/101240302206976 | 180168928/1368408064 |
| independent-compression | hist_u | N/A | N/A | N/A | N/A | N/A |
| independent-compression | hist_v | N/A | N/A | N/A | N/A | N/A |
| independent-compression | extreme_symbols | N/A | N/A | N/A | N/A | N/A |
| independent-compression | entropy_1024 | N/A | N/A | N/A | N/A | N/A |
| independent-compression | decompressed_norms | N/A | N/A | N/A | N/A | N/A |
| independent-compression | joint_uv_histogram | N/A | N/A | N/A | N/A | N/A |
| conditional-independent-given-pk | pk | 0.459211 | 2.024003 | 4.06711 | 1/73984 | 1395375/4194304 |

The former global `independent-output` construction is retained only as a software sanity check and is excluded from this scientific comparison.
