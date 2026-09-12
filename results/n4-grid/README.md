# n=4 grid artifacts

The grid and selection rule are fixed in
[`docs/transfer-and-n4-protocol.md`](../../docs/transfer-and-n4-protocol.md).
`screening.md` records the support and 12-key unconditional-failure screen;
`dimension-scaling.md` is the final scientific summary.

The two selected points each contain public and ciphertext results for 128
sampled outer keys with seed `20260913`. Encapsulation randomness conditional on
every sampled key is enumerated exactly. Each final law has total mass
`34359738368 = 128 * 2^28`.

The large joint-histogram laws are retained as lossless gzip files:

| Preset | File | SHA-256 |
|---|---|---|
| n4q29d43 | `final-ciphertext/joint_uv_histogram.csv.gz` | `0789E407EE3EC0D003CF59A5894B138519AE392C3C797D3E22DC5F465617BE4D` |
| n4q19d43 | `final-ciphertext/joint_uv_histogram.csv.gz` | `DB84C79B6E9D712E278B100E276B8637D0B6CF5FF401E53384FCBF1868621B76` |

Sample `D_infinity`, maximizing cells, and empirical frontiers describe these
specific sampled-key mixtures. They are not population bounds. The confidence
files concern the population mean over keys and distinguish the rigorous
Hoeffding interval from the narrower approximate normal interval.
