#!/usr/bin/env python3
"""Distribution-free confidence interval for an average over sampled keys."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def analyze(path: Path, alpha: float = 0.05):
    values = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            n, e = int(row["Nz"]), int(row["Ez"])
            values.append(e / n)
    if not values:
        raise ValueError("no sampled keys")
    mean = sum(values) / len(values)
    radius = math.sqrt(math.log(2.0 / alpha) / (2.0 * len(values)))
    variance = (sum((value - mean) ** 2 for value in values) / (len(values) - 1)
                if len(values) > 1 else 0.0)
    normal_radius = 1.959963984540054 * math.sqrt(variance / len(values))
    return {
        "method": "two-sided Hoeffding bound for iid key-level values in [0,1]",
        "alpha": alpha,
        "confidence": 1.0 - alpha,
        "sampled_keys": len(values),
        "mean_exact_conditional_failure": mean,
        "lower": max(0.0, mean - radius),
        "upper": min(1.0, mean + radius),
        "radius": radius,
        "sample_standard_deviation": math.sqrt(variance),
        "approximate_normal_interval": {
            "lower": max(0.0, mean - normal_radius),
            "upper": min(1.0, mean + normal_radius),
            "radius": normal_radius,
            "warning": "Approximate CLT interval; unlike the Hoeffding interval above, this is not a finite-sample distribution-free guarantee.",
        },
        "warning": "This interval concerns the population mean over keys; sampled maxima and D_infinity are not population bounds.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()
    if not 0.0 < args.alpha < 1.0:
        raise ValueError("alpha must lie in (0,1)")
    result = analyze(args.directory / "secret_key.csv", args.alpha)
    path = args.directory / "sampled_key_confidence.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
