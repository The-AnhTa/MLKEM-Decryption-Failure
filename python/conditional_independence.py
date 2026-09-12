#!/usr/bin/env python3
"""Derive the exact conditionally-independent-given-pk surrogate."""

from __future__ import annotations

import argparse
import csv
import json
import math
from fractions import Fraction
from pathlib import Path


def load_cells(path: Path):
    grouped = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pk = row["feature_value"]
            coordinate = int(row["coordinate"])
            grouped.setdefault(pk, {})[coordinate] = (int(row["Nz"]), int(row["Eiz"]))
    return grouped


def derive(path: Path):
    grouped = load_cells(path)
    raw = []
    total_mass = 0
    for pk, coordinates in grouped.items():
        ordered = [coordinates[i] for i in range(len(coordinates))]
        totals = {total for total, _ in ordered}
        if len(totals) != 1:
            raise ValueError(f"coordinate masses disagree for {pk}")
        nz = totals.pop()
        success = Fraction(1)
        for total, errors in ordered:
            if errors > total:
                raise ValueError(f"coordinate error mass exceeds total for {pk}")
            success *= Fraction(total - errors, total)
        raw.append((pk, nz, 1 - success, ordered))
        total_mass += nz
    cells = [(pk, Fraction(nz, total_mass), failure, coordinates)
             for pk, nz, failure, coordinates in raw]
    return total_mass, cells


def analyze_cells(total_mass, cells, max_bits=20):
    delta = sum((mass * failure for _, mass, failure, _ in cells), Fraction(0))
    if not delta:
        return {"delta": "0/1", "D2_bits": None, "Dinf_bits": None, "budgets": []}
    scored = sorted(cells, key=lambda cell: cell[2] / delta, reverse=True)
    d2 = sum((mass * (failure / delta) ** 2 for _, mass, failure, _ in cells), Fraction(0))
    max_lambda = scored[0][2] / delta
    budgets = []
    for bits in range(1, max_bits + 1):
        target = Fraction(1, 1 << bits)
        selected_mass = Fraction(0)
        selected_failures = Fraction(0)
        boundary_fraction = Fraction(0)
        for pk, mass, failure, _ in scored:
            if selected_mass + mass <= target:
                selected_mass += mass
                selected_failures += mass * failure
            else:
                boundary_fraction = (target - selected_mass) / mass
                selected_failures += (target - selected_mass) * failure
                selected_mass = target
                break
        amplification = (selected_failures / target) / delta
        budgets.append({
            "b": bits, "p": f"1/{1 << bits}",
            "amplification": f"{amplification.numerator}/{amplification.denominator}",
            "amplification_float": float(amplification),
            "G_bits": math.log2(float(amplification)) if amplification else None,
            "boundary_fraction": f"{boundary_fraction.numerator}/{boundary_fraction.denominator}",
        })
    best_pk, best_mass, best_failure, _ = scored[0]
    return {
        "delta": f"{delta.numerator}/{delta.denominator}",
        "delta_float": float(delta),
        "D2_bits": math.log2(float(d2)),
        "Dinf_bits": math.log2(float(max_lambda)),
        "maximizing_cell": {
            "feature_value": best_pk,
            "p": f"{best_mass.numerator}/{best_mass.denominator}",
            "conditional_failure": f"{best_failure.numerator}/{best_failure.denominator}",
            "amplification_float": float(max_lambda),
        },
        "budgets": budgets,
    }


def write_outputs(directory: Path):
    total_mass, cells = derive(directory / "pk_coordinate_marginals.csv")
    analysis = analyze_cells(total_mass, cells)
    with (directory / "pk_ci.csv").open("w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["feature_value", "Nz", "delta_ci_num", "delta_ci_den", "coordinate_errors"])
        for pk, mass, failure, coordinates in cells:
            nz = mass.numerator * (total_mass // mass.denominator)
            errors = ";".join(f"{e}/{n}" for n, e in coordinates)
            out.writerow([pk, nz, failure.numerator, failure.denominator, errors])
    (directory / "pk_ci_analysis.json").write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    frontier = {"selection": "randomized boundary-cell selection at exact mass p=2^-b",
                "budgets": analysis["budgets"]}
    (directory / "pk_ci_frontier_summary.json").write_text(json.dumps(frontier, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in analysis.items() if key != "budgets"}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    write_outputs(args.directory)


if __name__ == "__main__":
    main()
