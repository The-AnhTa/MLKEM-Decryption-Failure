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
`--mode independent-compression`. The global independent-output construction is
retained only as a software sanity check:

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

## Frozen-feature milestone

Feature definitions propagated beyond E0 are frozen in
[`docs/frozen-features.md`](docs/frozen-features.md). The first exact step is
`e1a = (n=2,k=1,q=19,eta1=eta2=1,du=3,dv=2)`:

```powershell
./build/toy-mlkem.exe --preset e1a --frozen-public --output results/e1a/public
./build/toy-mlkem.exe --preset e1a --ciphertext-dp --scalable-only `
  --output results/e1a/ciphertext
```

`python/conditional_independence.py` derives the exact coordinate-independent-
given-public-key surrogate from `pk_coordinate_marginals.csv`.

For sampled-key runs, `python/sampled_key_ci.py` reports a distribution-free
Hoeffding interval for the population mean. It does not interpret a sample
maximum or sampled `D_infinity` as a population bound.

## Parameter ladder

Presets `e0` through `e5`, including `e1a` through `e1c`, are available with
`--list-presets`. E0 and the E1 variants can be globally enumerated when
computationally affordable. Sampled outer keys with exact conditional
enumeration are supported, for example:

```powershell
./build/toy-mlkem.exe --preset e3 --sample-keys 100 --seed 2026 `
  --output results/e3
```

The seed and sample count are recorded in `metadata.json`. Global `k>1`
enumeration is rejected rather than silently changing the probability law.
For the current E2-E5 presets, exact support certificates prove that failure is
impossible for every key and encapsulation; see
[`results/milestone.md`](results/milestone.md). Sampling cannot estimate a
post-selection effect when the failure event has empty support.
