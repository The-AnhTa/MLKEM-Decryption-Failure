#!/usr/bin/env python3
"""Summarize the frozen-feature E0/E1 milestone and E2-E5 certificates."""

from __future__ import annotations

import json
from pathlib import Path


PUBLIC = ("at_norm_pair", "at_pair_histogram", "at_correlations", "at_projections")
CIPHERTEXT = ("hist_u", "hist_v", "extreme_symbols", "entropy_1024",
              "decompressed_norms", "joint_uv_histogram")


def metrics(directory: Path, feature: str):
    analysis = json.loads((directory / f"{feature}_analysis.json").read_text(encoding="utf-8"))
    budgets = json.loads((directory / f"{feature}_frontier_summary.json").read_text(encoding="utf-8"))["budgets"]
    b10 = next(item for item in budgets if item["b"] == 10)
    return {"D2_bits": analysis["D2_bits"], "Dinf_bits": analysis["Dinf_bits"],
            "G10_bits": b10["G_bits"], "A10": b10["amplification_float"]}


def build(root: Path):
    report = {"e0": {"public": {}, "ciphertext": {}}, "e1a": {"public": {}, "ciphertext": {}},
              "conditional_independence_given_pk": {}, "support_certificates": {}}
    for feature in PUBLIC:
        report["e0"]["public"][feature] = metrics(root / "e0" / "none", feature)
        report["e1a"]["public"][feature] = metrics(root / "e1a" / "public", feature)
    for feature in CIPHERTEXT:
        report["e0"]["ciphertext"][feature] = metrics(root / "e0" / "ciphertext-none", feature)
        report["e1a"]["ciphertext"][feature] = metrics(root / "e1a" / "ciphertext", feature)
    exact = json.loads((root / "e0" / "none" / "pk_analysis.json").read_text(encoding="utf-8"))
    ci = json.loads((root / "e0" / "none" / "pk_ci_analysis.json").read_text(encoding="utf-8"))
    report["conditional_independence_given_pk"] = {
        "exact_Dinf_bits": exact["Dinf_bits"], "ci_Dinf_bits": ci["Dinf_bits"],
        "exact_D2_bits": exact["D2_bits"], "ci_D2_bits": ci["D2_bits"],
        "interpretation": "conditional coordinate independence does not remove the E0 weak-key concentration",
    }
    for preset in ("e2", "e3", "e4", "e5"):
        report["support_certificates"][preset] = json.loads(
            (root / preset / "certificate" / "support_bound.json").read_text(encoding="utf-8"))
    return report


def write(root: Path):
    report = build(root)
    (root / "milestone.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (root / "milestone.md").open("w", encoding="utf-8") as out:
        out.write("# Frozen-feature propagation milestone\n\n")
        out.write("All feature definitions were frozen before E1a was inspected. Values below use randomized boundary-cell selection at exactly `p=2^-10`.\n\n")
        out.write("| Family | Feature | E0 Dinf | E0 G(10) | E1a Dinf | E1a G(10) |\n")
        out.write("|---|---|---:|---:|---:|---:|\n")
        for family, features in (("public", PUBLIC), ("ciphertext", CIPHERTEXT)):
            for feature in features:
                e0 = report["e0"][family][feature]
                e1 = report["e1a"][family][feature]
                out.write(f"| {family} | {feature} | {e0['Dinf_bits']:.6f} | {e0['G10_bits']:.6f} | "
                          f"{e1['Dinf_bits']:.6f} | {e1['G10_bits']:.6f} |\n")
        comparison = report["conditional_independence_given_pk"]
        out.write("\n## Conditional independence given public key\n\n")
        out.write(f"Exact `Dinf(pk) = {comparison['exact_Dinf_bits']:.6f}` bits; conditional-independent "
                  f"`Dinf(pk) = {comparison['ci_Dinf_bits']:.6f}` bits. Cross-coordinate dependence therefore "
                  "does not explain the E0 weak-key concentration.\n\n")
        out.write("## E2-E5 support certificates\n\n")
        out.write("| Preset | Noise bound | Decoding margin | Failure possible? |\n")
        out.write("|---|---:|---:|---:|\n")
        for preset, certificate in report["support_certificates"].items():
            out.write(f"| {preset} | {certificate['total_noise_bound']} | {certificate['decoding_margin']} | "
                      f"{'no' if certificate['failure_impossible'] else 'yes'} |\n")
        out.write("\nThe E2-E5 toy configurations cannot answer a post-selection question because their failure event has empty support. The next parameter ladder must scale noise with `q` or choose compression/dimensions that retain nonzero failure support.\n")
    print(root / "milestone.md")


if __name__ == "__main__":
    write(Path("results"))
