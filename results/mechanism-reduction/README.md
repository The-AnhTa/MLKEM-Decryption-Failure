# Mechanism-reduction results

This directory contains the strict mechanism-reduction study specified in
[`../../docs/mechanism-reduction-protocol.md`](../../docs/mechanism-reduction-protocol.md).
It compares the unchanged E0-frozen marginal ciphertext score with a fixed set
of transparent, dimensionless public ciphertext statistics. No statistic is
selected or reoriented using E1a or either n=4 dataset.

Run the full experiment with:

```powershell
./scripts/run-mechanism-reduction.ps1
```

Regenerate the analysis, 10,000-replicate outer-key bootstrap, figures, and
report from the committed sufficient statistics with:

```powershell
./scripts/run-mechanism-reduction.ps1 -ReuseData
```

E0 and E1a are exact finite distributions. Each n=4 result is an empirical
mixture of 128 sampled outer keys (seed `20260913`) with exact enumeration of
the inner encapsulation randomness. The decoding margin is retained only for
diagnosis and is never used as a public predictor.

The frozen configuration SHA-256 is
`4CBD0107C701F65B66745502A01C02C78A4E4AC6A4FAC3C0DDAF24F6B1F14395`.
Large sufficient-statistic tables are stored as deterministic gzip streams;
q19 streams are split into 90 MiB binary parts for GitHub. Concatenating parts
in lexical order recovers the archive whose hash is listed here:

| Dataset/file | gzip-stream SHA-256 |
|---|---|
| q29 aggregate | `FA8D62F0DDFC4B069592F6B8A48D6EC0D8BA644C9CEA00C492A1DCB9DB3A8A5A` |
| q29 by key | `F45934B5CF83C8B49D3A26856DFF457BE9D2869C3E8A03E38F0058BB4C83EB04` |
| q19 aggregate | `1B2639D805266D7AC0CAB26F323B7E6841DE10BCD9A4BE03B2B4EC699B3BE114` |
| q19 by key | `1F660EF4399EF4144BE3773849DD17AD22B25B00ADE47BB578B238753FF65A8D` |
