#!/usr/bin/env python3
"""Analyze exact (Nz, Ez) tables emitted by toy-mlkem."""

from __future__ import annotations

import argparse
import csv
import gzip
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


def open_law(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open(newline="", encoding="utf-8")


def streaming_metrics(path: Path, with_ratio_groups=False):
    """Compute summary statistics in bounded memory; does not build a frontier."""
    total = failures = 0
    d2_sum = 0.0
    d2_compensation = 0.0
    best = None
    groups = {}
    with open_law(path) as handle:
        for row in csv.DictReader(handle):
            z, n, e = row["feature_value"], int(row["Nz"]), int(row["Ez"])
            total += n
            failures += e
            if e:
                term = (e * e) / n
                corrected = term - d2_compensation
                updated = d2_sum + corrected
                d2_compensation = (updated - d2_sum) - corrected
                d2_sum = updated
                if best is None or e * best[1] > best[2] * n:
                    best = (z, n, e)
            if with_ratio_groups:
                divisor = math.gcd(e, n)
                ratio = (e // divisor, n // divisor)
                group_n, group_e = groups.get(ratio, (0, 0))
                groups[ratio] = (group_n + n, group_e + e)
    if failures == 0:
        result = (total, failures, None, None, best)
        return result + ([],) if with_ratio_groups else result
    d2 = math.log2(total * d2_sum / (failures * failures))
    assert best is not None
    dinf = math.log2(best[2] * total / (best[1] * failures))
    result = (total, failures, d2, dinf, best)
    if with_ratio_groups:
        ratio_rows = [(f"q={num}/{den}", n, e) for (num, den), (n, e) in groups.items()]
        return result + (ratio_rows,)
    return result


def write_frontier(path: Path, frontier):
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["rank", "feature_value", "p_num", "p_den", "A_num", "A_den", "s_bits", "g_bits"])
        for rank, (z, p, amp) in enumerate(frontier, 1):
            out.writerow([rank, z, p.numerator, p.denominator, amp.numerator, amp.denominator,
                          -math.log2(float(p)), math.log2(float(amp))])


def budgeted_frontier(rows, max_bits=20):
    """Neyman-Pearson frontier with randomized selection inside a boundary cell."""
    total = sum(n for _, n, _ in rows)
    failures = sum(e for _, _, e in rows)
    if failures == 0:
        return []
    scored = sorted(rows, key=lambda row: Fraction(row[2], row[1]), reverse=True)
    output = []
    for bits in range(1, max_bits + 1):
        target = Fraction(total, 1 << bits)
        index = 0
        cumulative_n = 0
        cumulative_e = Fraction(0)
        while index < len(scored) and cumulative_n + scored[index][1] <= target:
            _, n, e = scored[index]
            cumulative_n += n
            cumulative_e += e
            index += 1
        selected_failures = cumulative_e
        boundary_fraction = Fraction(0)
        boundary_value = None
        if cumulative_n < target and index < len(scored):
            boundary_value, n, e = scored[index]
            boundary_fraction = (target - cumulative_n) / n
            selected_failures += boundary_fraction * e
        conditional = selected_failures / target
        amplification = conditional / Fraction(failures, total)
        output.append({
            "b": bits,
            "p": f"1/{1 << bits}",
            "amplification": f"{amplification.numerator}/{amplification.denominator}",
            "amplification_float": float(amplification),
            "G_bits": math.log2(float(amplification)) if amplification else None,
            "conditional_failure": f"{conditional.numerator}/{conditional.denominator}",
            "boundary_fraction": f"{boundary_fraction.numerator}/{boundary_fraction.denominator}",
            "boundary_cell": boundary_value,
        })
    return output


def write_budgeted_frontier(path: Path, rows):
    payload = {
        "selection": "randomized boundary-cell selection at exact mass p=2^-b",
        "budgets": budgeted_frontier(rows),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def independent_output(source: Path, output: Path):
    marginals = []
    with (source / "coordinate_marginals.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            marginals.append((int(row["total"]), int(row["correct"])))
    denominator = math.prod(total for total, _ in marginals)
    correct = math.prod(value for _, value in marginals)
    failure = denominator - correct
    output.mkdir(parents=True, exist_ok=True)
    derived = []
    for feature_id in ("pk", "t_norm2", "t_histogram", "t_autocorrelation"):
        feature_path = source / f"{feature_id}.csv"
        if not feature_path.exists():
            continue
        rows = load_law(feature_path)
        with (output / f"{feature_id}.csv").open("w", newline="", encoding="utf-8") as handle:
            out = csv.writer(handle)
            out.writerow(["feature_id", "feature_value", "Nz", "Ez"])
            for z, n, _ in rows:
                out.writerow([feature_id, z, n * denominator, n * failure])
        derived.append(feature_id)
    metadata = {
        "schema_version": 1,
        "mode": "independent-output",
        "source": str(source),
        "definition": "key prior times product of global honest one-coordinate marginals",
        "derived_features": derived,
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
    parser.add_argument("--summary-only", action="store_true",
                        help="stream the law without constructing the oracle frontier")
    args = parser.parse_args()
    if args.derive_independent_output:
        independent_output(args.directory, args.derive_independent_output)
    law_path = args.directory / f"{args.feature}.csv"
    if not law_path.exists() and law_path.with_suffix(law_path.suffix + ".gz").exists():
        law_path = law_path.with_suffix(law_path.suffix + ".gz")
    rows = None
    streaming_best = None
    if args.summary_only:
        total, failures, d2, dinf, streaming_best, ratio_rows = streaming_metrics(law_path, with_ratio_groups=True)
        frontier = []
        plotted = False
        write_budgeted_frontier(args.directory / f"{args.feature}_frontier_summary.json", ratio_rows)
    else:
        rows = load_law(law_path)
        total, failures, d2, dinf, frontier = metrics(rows)
        write_frontier(args.directory / f"{args.feature}_frontier.csv", frontier)
        write_budgeted_frontier(args.directory / f"{args.feature}_frontier_summary.json", rows)
        plotted = plot_frontier(args.directory / f"{args.feature}_frontier.png", frontier)
    margin_cdf_written = write_margin_cdf(args.directory)
    best = None
    if streaming_best:
        z, n, e = streaming_best
        amp = Fraction(e * total, n * failures)
        best = {
            "feature_value": z, "p": f"{n}/{total}",
            "conditional_failure": f"{e}/{n}",
            "amplification": f"{amp.numerator}/{amp.denominator}",
            "amplification_float": float(amp),
        }
    elif frontier:
        z, p, amp = frontier[0]
        matching = next((item for item in rows if item[0] == z), None)
        if matching:
            _, n, e = matching
            best = {
                "feature_value": z,
                "p": f"{n}/{total}",
                "conditional_failure": f"{e}/{n}",
                "amplification": f"{amp.numerator}/{amp.denominator}",
                "amplification_float": float(amp),
            }
    summary = {"N": str(total), "E": str(failures), "delta": f"{failures}/{total}",
               "D2_bits": d2, "Dinf_bits": dinf, "plot_written": plotted,
               "margin_cdf_written": margin_cdf_written, "summary_only": args.summary_only,
               "maximizing_cell": best}
    (args.directory / f"{args.feature}_analysis.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
