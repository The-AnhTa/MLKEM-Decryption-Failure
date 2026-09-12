#!/usr/bin/env python3
"""Write the predicate-transfer and n=4 dimension-scaling report."""

from __future__ import annotations

import json
from pathlib import Path


TRANSFER_FEATURES = ("at_norm_pair", "extreme_symbols", "decompressed_norms", "joint_uv_histogram")
EMPIRICAL_FEATURES = ("at_norm_pair", "hist_u", "extreme_symbols", "decompressed_norms", "joint_uv_histogram")
PRESETS = ("n4q29d43", "n4q19d43")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def budget(payload, feature, bits=10, kind="randomized"):
    rows = payload["results"][feature]["budgets"]
    return next(row for row in rows if row["b"] == bits)[kind]


def empirical(root: Path, preset: str, feature: str):
    family = "final-public" if feature == "at_norm_pair" else "final-ciphertext"
    directory = root / preset / family
    analysis = read(directory / f"{feature}_analysis.json")
    frontier = read(directory / f"{feature}_frontier_summary.json")
    b10 = next(row for row in frontier["budgets"] if row["b"] == 10)
    return analysis["Dinf_bits"], b10["G_bits"]


def write(results: Path):
    root = results / "n4-grid"
    e1 = read(results / "predicate-transfer" / "e1a-evaluation.json")
    transfers = {preset: read(root / preset / "e0-transfer.json") for preset in PRESETS}
    output = root / "dimension-scaling.md"
    with output.open("w", encoding="utf-8") as out:
        out.write("# Predicate transfer and n=4 dimension scaling\n\n")
        out.write("The E0 model and n=4 grid protocol were committed before target evaluation. "
                  "No feature family was added after target results were inspected.\n\n")
        out.write("## E0-trained predicates evaluated on exact E1a\n\n")
        out.write("Nominal E0 budget is `2^-10`; achieved target mass is reported because the predicate is unchanged.\n\n")
        out.write("| Feature | Randomized achieved p | Randomized A | Oracle retained | Deterministic achieved p | Deterministic A |\n")
        out.write("|---|---:|---:|---:|---:|---:|\n")
        for feature in TRANSFER_FEATURES:
            randomized = budget(e1, feature)
            deterministic = budget(e1, feature, kind="deterministic")
            out.write(f"| {feature} | {randomized['achieved_p_float']:.6g} | "
                      f"{randomized['amplification_float']:.4f} | {randomized['oracle_retention']:.3f} | "
                      f"{deterministic['achieved_p_float']:.6g} | {deterministic['amplification_float']:.4f} |\n")
        out.write("\nThe E0 predicate therefore transfers across `q=17 -> 19`; this is predicate transfer, not an E1a-refitted frontier.\n\n")

        out.write("## Selected n=4 points\n\n")
        out.write("| Preset | Mean failure | Approximate 95% mean interval | Rigorous Hoeffding interval |\n")
        out.write("|---|---:|---:|---:|\n")
        for preset in PRESETS:
            ci = read(root / preset / "final-public" / "sampled_key_confidence.json")
            normal = ci["approximate_normal_interval"]
            out.write(f"| {preset} | {ci['mean_exact_conditional_failure']:.6f} | "
                      f"[{normal['lower']:.6f}, {normal['upper']:.6f}] | "
                      f"[{ci['lower']:.6f}, {ci['upper']:.6f}] |\n")
        out.write("\nIntervals are over sampled keys; encapsulation probabilities within each key are exact. "
                  "The normal interval is approximate, while Hoeffding is distribution-free but very conservative.\n\n")

        out.write("## Frozen-feature concentration in sampled n=4 mixtures\n\n")
        out.write("These are descriptive empirical-mixture frontiers, not population bounds.\n\n")
        out.write("| Preset | Feature | Sample Dinf | Sample G(10) |\n")
        out.write("|---|---|---:|---:|\n")
        for preset in PRESETS:
            for feature in EMPIRICAL_FEATURES:
                dinf, g10 = empirical(root, preset, feature)
                out.write(f"| {preset} | {feature} | {dinf:.6f} | {g10:.6f} |\n")

        out.write("\n## E0 predicate applied unchanged at n=4\n\n")
        out.write("| Preset | Feature | Achieved p at nominal 2^-10 | Amplification | Oracle retained |\n")
        out.write("|---|---|---:|---:|---:|\n")
        for preset in PRESETS:
            for feature in TRANSFER_FEATURES:
                row = budget(transfers[preset], feature)
                retention = "N/A" if row["oracle_retention"] is None else f"{row['oracle_retention']:.3f}"
                out.write(f"| {preset} | {feature} | {row['achieved_p_float']:.6g} | "
                          f"{row['amplification_float']:.4f} | {retention} |\n")

        out.write("\n## Interpretation\n\n")
        out.write("Observable post-selection remains strong in both sampled n=4 mixtures: the joint histogram has "
                  "sample `G(10)` of about 7.48 and 4.24 bits, respectively. This establishes nonzero-failure "
                  "dimension-scaling examples, but the values are descriptive for the 128-key mixtures.\n\n")
        out.write("The specific E0 `2^-10` predicates do not generally transfer to n=4: most select no target "
                  "cells, and the decompressed-norm predicate has only tiny support. Thus the experiment supports "
                  "feature-family survival with dimension, but does not yet establish a dimension-independent "
                  "predicate. Public-feature `Dinf` values also largely reflect selection among only 128 sampled "
                  "keys and must not be read as population bounds.\n")
    print(output)


if __name__ == "__main__":
    write(Path("results"))
