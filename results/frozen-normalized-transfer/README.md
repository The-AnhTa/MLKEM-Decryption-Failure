# Frozen normalized transfer results

This directory contains the strict E0-trained normalized ciphertext-score
transfer study specified in
[`../../docs/frozen-normalized-transfer-protocol.md`](../../docs/frozen-normalized-transfer-protocol.md).

The concise interpretation is in [`report.md`](report.md). The main table is
[`transfer-summary.csv`](transfer-summary.csv); joint-versus-marginal results,
weighted AUCs, and their cluster-bootstrap intervals are in
[`joint-vs-marginal.csv`](joint-vs-marginal.csv). Exact ROC coordinates and
margin diagnostics are also retained.

The frozen model SHA-256 is
`1D279C146E2EEE4F3ADCEB01B22132025D8E21C2D66543AE65797C52496A6228`.
The model is trained only from `data/e0/normalized_uv_margin.csv`.

The sampled n=4 laws preserve key identity for cluster bootstrap and are
losslessly, deterministically compressed:

| Dataset | File SHA-256 |
|---|---|
| n4q29d43 | `1C8BA7855E0B9275B3E9C30F531C4C80968F79D6FFE5B74EC05617306C5C50E0` |
| n4q19d43 | `35FFDBE3CDDF9DDBEA1E5BD0A6456BB224F543589E211E0167D387167AD995FA` |

E0 and E1a are globally exact. Each n=4 law is an empirical mixture of 128
sampled keys (seed `20260913`) with exact conditional enumeration of all inner
encapsulation randomness. Bootstrap intervals therefore quantify sampled-key
uncertainty only.
