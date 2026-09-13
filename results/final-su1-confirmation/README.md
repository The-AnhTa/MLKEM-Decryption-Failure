# Final frozen-Su1 confirmation

This directory holds the independent confirmatory experiment specified in
[`../../docs/final-su1-confirmation-protocol.md`](../../docs/final-su1-confirmation-protocol.md).
Only the previously selected, positively oriented `S_u1` statistic is used.

Run the complete support selection, preregistration verification, new-data
generation, exact conditional analysis, and 10,000-replicate key-cluster
bootstrap with:

```powershell
./scripts/run-final-su1-confirmation.ps1
```

After data are generated, reproduce the analysis with:

```powershell
./scripts/run-final-su1-confirmation.ps1 -ReuseData
```

The analysis refuses to run if the preregistration or any hashed analysis/C++
source differs from the frozen version.

The immutable preregistration SHA-256 is
`83FEFB703D01E3939E8FE81364A67EC4BD5BA5E43759033FDD28D39C6E6FCC5C`.
The selected point was `n8q29d43`. Under the preregistered formal rule the
result is **not confirmed**; see [`report.md`](report.md) and
[`summary.csv`](summary.csv). This negative confirmatory result is retained
without selecting a fallback point or changing the statistic.
