#!/usr/bin/env python3
"""Apply the predeclared n=4 support, failure-rate, and selection rules."""

from __future__ import annotations

import csv
import json
import math
from fractions import Fraction
from pathlib import Path


PRESETS = tuple(f"n4q{q}d{du}{dv}"
                for q in (17, 19, 23, 29)
                for du, dv in ((3, 2), (4, 2), (4, 3)))


def global_failure(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected one global cell in {path}")
    n, e = int(rows[0]["Nz"]), int(rows[0]["Ez"])
    return n, e, Fraction(e, n)


def choose(rows):
    eligible = [row for row in rows if row["support_possible"] and
                Fraction(1, 1000) <= row["delta_exact"] <= Fraction(1, 10)]
    selected = []
    for target in (0.01, 0.05):
        remaining = [row for row in eligible if row not in selected]
        if not remaining:
            break
        selected.append(min(remaining, key=lambda row:
                            (abs(math.log(row["delta_float"]) - math.log(target)), row["preset"])))
    return selected


def build(root: Path):
    rows = []
    for preset in PRESETS:
        directory = root / preset
        certificate = json.loads((directory / "certificate" / "support_bound.json").read_text(encoding="utf-8"))
        n, e, delta = global_failure(directory / "pilot" / "global.csv")
        rows.append({"preset": preset, "support_possible": not certificate["failure_impossible"],
                     "noise_bound": certificate["total_noise_bound"],
                     "decoding_margin": certificate["decoding_margin"],
                     "N": str(n), "E": str(e), "delta_exact": delta,
                     "delta_float": float(delta)})
    selected = choose(rows)
    return rows, selected


def write(root: Path):
    rows, selected = build(root)
    payload_rows = []
    for row in rows:
        item = dict(row)
        item["delta_exact"] = f"{row['delta_exact'].numerator}/{row['delta_exact'].denominator}"
        item["eligible"] = Fraction(1, 1000) <= row["delta_exact"] <= Fraction(1, 10)
        item["selected"] = row in selected
        payload_rows.append(item)
    payload = {"protocol": "docs/transfer-and-n4-protocol.md", "pilot_keys": 12,
               "seed": 20260912, "selected": [row["preset"] for row in selected],
               "points": payload_rows}
    (root / "screening.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with (root / "screening.md").open("w", encoding="utf-8") as out:
        out.write("# Predeclared n=4 grid screening\n\n")
        out.write("All pilot values average 12 sampled keys with exact encapsulation enumeration.\n\n")
        out.write("| Preset | Bound | Margin | Pilot failure | Eligible | Selected |\n")
        out.write("|---|---:|---:|---:|---:|---:|\n")
        for row in payload_rows:
            out.write(f"| {row['preset']} | {row['noise_bound']} | {row['decoding_margin']} | "
                      f"{row['delta_float']:.6f} | {'yes' if row['eligible'] else 'no'} | "
                      f"{'yes' if row['selected'] else 'no'} |\n")
        out.write("\nSelected by the frozen rule: `" + "`, `".join(payload["selected"]) + "`.\n")
    return payload


if __name__ == "__main__":
    write(Path("results/n4-grid"))
