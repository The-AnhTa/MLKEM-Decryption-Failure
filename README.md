# Exact toy ML-KEM decryption-failure experiment

This project computes exact finite joint distributions `(Z,F)` for a miniature
coefficient-domain ML-KEM model. It uses weighted CBD support, exact integer
compression, negacyclic multiplication, and no coefficient-independence
assumption.

The baseline E0 parameters are

```text
(n,k,q,eta1,eta2,du,dv) = (2,1,17,1,1,3,2)
```

See [problem.md](problem.md) for the research question and
[docs/e0-spec.md](docs/e0-spec.md) for the executable probability laws.

## Build and test on Windows

Run directly from PowerShell:

```powershell
./scripts/build.ps1
```

## Run

```powershell
./build/toy-mlkem.exe --preset e0 --mode none --output results/e0/none
python python/analyze.py results/e0/none --feature pk
```

Ablations use `--mode no-compression` and
`--mode independent-compression`. The independent-output ablation is derived
exactly from the normal coordinate marginals:

```powershell
python python/analyze.py results/e0/none --feature pk `
  --derive-independent-output results/e0/independent-output
```

`--max-outer N` runs a deterministic prefix for smoke tests (per sampled key
when combined with `--sample-keys`). Such output is not a probability experiment
and must not be reported as a scientific result.

The complete E0 observable/ablation study, including exact ciphertext dynamic
programs and the combined matrix, is run by:

```powershell
./scripts/run-e0.ps1
```

Results are intentionally version-controlled under `results/e0/`.
The baseline `(pk,c)` law is stored losslessly as `pk_ciphertext.csv.gz` because
the uncompressed CSV exceeds GitHub's ordinary per-file limit. The much larger
no-compression `(pk,c)` table is streamed into its exact summary and then removed;
it can be reproduced with `run-e0.ps1`.

## Parameter ladder

Presets `e0` through `e5` are available with `--list-presets`. E0 and E1 can be
globally enumerated when computationally affordable. E2-E5 use sampled outer
keys with exact conditional enumeration, for example:

```powershell
./build/toy-mlkem.exe --preset e3 --sample-keys 100 --seed 2026 `
  --output results/e3
```

The seed and sample count are recorded in `metadata.json`. Global `k>1`
enumeration is rejected rather than silently changing the probability law.
