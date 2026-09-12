#!/usr/bin/env python3
"""Build the E0 observable/ablation matrix from analysis JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


OBSERVABLES = (
    "pk", "ciphertext", "pk_ciphertext", "ciphertext_symbols",
    "t_norm2", "t_histogram", "t_autocorrelation",
    "at_norm_pair", "at_pair_histogram", "at_correlations", "at_projections",
    "hist_u", "hist_v", "extreme_symbols", "entropy_1024",
    "decompressed_norms", "joint_uv_histogram",
)

CIPHERTEXT_OBSERVABLES = {
    "ciphertext", "pk_ciphertext", "ciphertext_symbols", "hist_u", "hist_v",
    "extreme_symbols", "entropy_1024", "decompressed_norms", "joint_uv_histogram",
}


def analysis_directory(root: Path, mode: str, observable: str) -> Path:
    if observable in CIPHERTEXT_OBSERVABLES:
        if mode == "none":
            return root / "ciphertext-none"
        if mode == "no-compression":
            return root / "ciphertext-no-compression"
        return root / "undefined-ciphertext-observable"
    return root / mode


def collect(root: Path):
    rows = []
    for mode in ("none", "no-compression", "independent-compression"):
        for observable in OBSERVABLES:
            path = analysis_directory(root, mode, observable) / f"{observable}_analysis.json"
            if not path.exists():
                rows.append({"mode": mode, "observable": observable, "status": "N/A"})
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            best = data.get("maximizing_cell") or {}
            dinf = data.get("Dinf_bits")
            rows.append({
                "mode": mode,
                "observable": observable,
                "status": "ok",
                "D2_bits": data.get("D2_bits"),
                "Dinf_bits": dinf,
                "max_amplification": None if dinf is None else 2.0 ** dinf,
                "p_z_star": best.get("p"),
                "failure_given_z_star": best.get("conditional_failure"),
                "z_star": best.get("feature_value"),
            })
    ci_path = root / "none" / "pk_ci_analysis.json"
    if ci_path.exists():
        data = json.loads(ci_path.read_text(encoding="utf-8"))
        best = data.get("maximizing_cell") or {}
        rows.append({
            "mode": "conditional-independent-given-pk", "observable": "pk", "status": "ok",
            "D2_bits": data.get("D2_bits"), "Dinf_bits": data.get("Dinf_bits"),
            "max_amplification": best.get("amplification_float"), "p_z_star": best.get("p"),
            "failure_given_z_star": best.get("conditional_failure"), "z_star": best.get("feature_value"),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("results/e0"))
    args = parser.parse_args()
    rows = collect(args.root)
    columns = ("mode", "observable", "status", "D2_bits", "Dinf_bits",
               "max_amplification", "p_z_star", "failure_given_z_star", "z_star")
    with (args.root / "observable_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        out = csv.DictWriter(handle, fieldnames=columns)
        out.writeheader()
        out.writerows(rows)
    with (args.root / "observable_matrix.md").open("w", encoding="utf-8") as out:
        out.write("# E0 observable and ablation matrix\n\n")
        out.write("| Mode | Observable | D2 (bits) | Dinf (bits) | max amplification | p(z*) | Pr[F|z*] |\n")
        out.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for row in rows:
            if row["status"] != "ok":
                out.write(f"| {row['mode']} | {row['observable']} | N/A | N/A | N/A | N/A | N/A |\n")
                continue
            out.write(f"| {row['mode']} | {row['observable']} | {row['D2_bits']:.6f} | "
                      f"{row['Dinf_bits']:.6f} | {row['max_amplification']:.6g} | "
                      f"{row['p_z_star']} | {row['failure_given_z_star']} |\n")
        out.write("\nThe former global `independent-output` construction is retained only as a software sanity check and is excluded from this scientific comparison.\n")
    print(f"wrote {args.root / 'observable_matrix.csv'} and observable_matrix.md")


if __name__ == "__main__":
    main()
