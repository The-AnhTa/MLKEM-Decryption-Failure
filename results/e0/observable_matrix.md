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
| no-compression | pk | 2.087217 | 2.900464 | 7.46667 | 16384/1212153856 | 224/16384 |
| no-compression | ciphertext | 3.071468 | 8.093109 | 273.067 | 1152/1212153856 | 576/1152 |
| no-compression | pk_ciphertext | 8.925759 | 9.093109 | 546.133 | 2/1212153856 | 2/2 |
| no-compression | ciphertext_symbols | N/A | N/A | N/A | N/A | N/A |
| no-compression | t_norm2 | 0.374108 | 0.415037 | 1.33333 | 25165824/1212153856 | 61440/25165824 |
| no-compression | t_histogram | 0.374108 | 0.415037 | 1.33333 | 6291456/1212153856 | 15360/6291456 |
| no-compression | t_autocorrelation | 0.278573 | 0.415037 | 1.33333 | 12582912/1212153856 | 30720/12582912 |
| independent-compression | pk | 0.471966 | 1.240310 | 2.36249 | 1368408064/101240302206976 | 180168928/1368408064 |
| independent-compression | ciphertext | N/A | N/A | N/A | N/A | N/A |
| independent-compression | pk_ciphertext | N/A | N/A | N/A | N/A | N/A |
| independent-compression | ciphertext_symbols | N/A | N/A | N/A | N/A | N/A |
| independent-compression | t_norm2 | 0.247279 | 0.329470 | 1.25655 | 2101874786304/101240302206976 | 147190882176/2101874786304 |
| independent-compression | t_histogram | 0.247279 | 0.329470 | 1.25655 | 525468696576/101240302206976 | 36797720544/525468696576 |
| independent-compression | t_autocorrelation | 0.170732 | 0.329470 | 1.25655 | 1050937393152/101240302206976 | 73595441088/1050937393152 |
| independent-output | pk | 0.000000 | 0.000000 | 1 | 1540690511780295460519936/1781038231618021552361046016 | 127095306018904218796032/1540690511780295460519936 |
| independent-output | ciphertext | N/A | N/A | N/A | N/A | N/A |
| independent-output | pk_ciphertext | N/A | N/A | N/A | N/A | N/A |
| independent-output | ciphertext_symbols | N/A | N/A | N/A | N/A | N/A |
| independent-output | t_norm2 | 0.000000 | 0.000000 | 1 | 115936961011467233404125184/1781038231618021552361046016 | 9563921777922542464401408/115936961011467233404125184 |
| independent-output | t_histogram | 0.000000 | 0.000000 | 1 | 120559032546808119785684992/1781038231618021552361046016 | 9945207695979255120789504/120559032546808119785684992 |
| independent-output | t_autocorrelation | 0.000000 | 0.000000 | 1 | 18488286141363545526239232/1781038231618021552361046016 | 1525143672226850625552384/18488286141363545526239232 |
