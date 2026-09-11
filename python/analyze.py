#!/usr/bin/env python3
"""Analyze exact (Nz, Ez) tables emitted by toy-mlkem."""

from __future__ import annotations

import argparse
import csv
import json
import math
from fractions import Fraction
from pathlib import Path


def load_law(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append((row["feature_value"], int(row["Nz"]), int(row["Ez"])))
    if not rows:
        raise ValueError(f"empty law: {path}")
    return rows


def metrics(rows):
    total = sum(n for _, n, _ in rows)
    failures = sum(e for _, _, e in rows)
    if failures == 0:
        return total, failures, None, None, []
    scored = []
    d2_sum = Fraction(0)
    max_lambda = Fraction(0)
    for z, n, e in rows:
        lam = Fraction(e * total, n * failures)
        max_lambda = max(max_lambda, lam)
        d2_sum += Fraction(e * e * total, n * failures * failures)
        scored.append((lam, z, n, e))
    scored.sort(reverse=True, key=lambda item: item[0])
    frontier = []
    cumulative_n = cumulative_e = 0
    for _, z, n, e in scored:
        cumulative_n += n
        cumulative_e += e
        p = Fraction(cumulative_n, total)
        amp = Fraction(cumulative_e * total, cumulative_n * failures)
        if amp > 1 / p:
            raise AssertionError("universal amplification bound violated")
        frontier.append((z, p, amp))
    return total, failures, math.log2(float(d2_sum)), math.log2(float(max_lambda)), frontier


def write_frontier(path: Path, frontier):
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["rank", "feature_value", "p_num", "p_den", "A_num", "A_den", "s_bits", "g_bits"])
        for rank, (z, p, amp) in enumerate(frontier, 1):
            out.writerow([rank, z, p.numerator, p.denominator, amp.numerator, amp.denominator,
                          -math.log2(float(p)), math.log2(float(amp))])


def independent_output(source: Path, output: Path):
    pk_rows = load_law(source / "pk.csv")
    marginals = []
    with (source / "coordinate_marginals.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            marginals.append((int(row["total"]), int(row["correct"])))
    denominator = math.prod(total for total, _ in marginals)
    correct = math.prod(value for _, value in marginals)
    failure = denominator - correct
    output.mkdir(parents=True, exist_ok=True)
    with (output / "pk.csv").open("w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["feature_id", "feature_value", "Nz", "Ez"])
        for z, n, _ in pk_rows:
            out.writerow(["pk", z, n * denominator, n * failure])
    metadata = {
        "schema_version": 1,
        "mode": "independent-output",
        "source": str(source),
        "definition": "key prior times product of global honest one-coordinate marginals",
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def write_margin_cdf(directory: Path):
    source = directory / "norm_margin.csv"
    if not source.exists():
        return False
    grouped = {}
    for feature, n, _ in load_law(source):
        coarse, margin_text = feature.rsplit("|M=", 1)
        margin = int(margin_text)
        grouped.setdefault(coarse, {})[margin] = grouped.setdefault(coarse, {}).get(margin, 0) + n
    with (directory / "norm_margin_cdf.csv").open("w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["t_norm2", "margin", "cumulative_weight", "total_weight"])
        for coarse, distribution in sorted(grouped.items()):
            total = sum(distribution.values())
            cumulative = 0
            for margin, weight in sorted(distribution.items()):
                cumulative += weight
                out.writerow([coarse, margin, cumulative, total])
    return True


def plot_frontier(path: Path, frontier):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    s = [-math.log2(float(p)) for _, p, _ in frontier]
    g = [math.log2(float(a)) for _, _, a in frontier]
    upper = max(s) if s else 1
    plt.figure(figsize=(7, 5))
    plt.plot(s, g, label="oracle frontier")
    plt.plot([0, upper], [0, 0], "--", label="independence")
    plt.plot([0, upper], [0, upper], ":", label="universal bound")
    plt.xlabel("selection cost s = -log2(p)")
    plt.ylabel("amplification g = log2(A)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--feature", default="pk")
    parser.add_argument("--derive-independent-output", type=Path)
    args = parser.parse_args()
    if args.derive_independent_output:
        independent_output(args.directory, args.derive_independent_output)
    rows = load_law(args.directory / f"{args.feature}.csv")
    total, failures, d2, dinf, frontier = metrics(rows)
    write_frontier(args.directory / f"{args.feature}_frontier.csv", frontier)
    plotted = plot_frontier(args.directory / f"{args.feature}_frontier.png", frontier)
    margin_cdf_written = write_margin_cdf(args.directory)
    summary = {"N": str(total), "E": str(failures), "delta": f"{failures}/{total}",
               "D2_bits": d2, "Dinf_bits": dinf, "plot_written": plotted,
               "margin_cdf_written": margin_cdf_written}
    (args.directory / f"{args.feature}_analysis.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
