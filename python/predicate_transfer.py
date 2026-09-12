#!/usr/bin/env python3
"""Train selectors on E0 only and evaluate the frozen predicates elsewhere."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from fractions import Fraction
from pathlib import Path


FEATURES = {
    "at_norm_pair": ("public", "none"),
    "hist_u": ("ciphertext", "ciphertext-none"),
    "hist_v": ("ciphertext", "ciphertext-none"),
    "extreme_symbols": ("ciphertext", "ciphertext-none"),
    "entropy_1024": ("ciphertext", "ciphertext-none"),
    "decompressed_norms": ("ciphertext", "ciphertext-none"),
    "joint_uv_histogram": ("ciphertext", "ciphertext-none"),
}


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def parse_fraction(value: str) -> Fraction:
    numerator, denominator = value.split("/", 1)
    return Fraction(int(numerator), int(denominator))


def load_params(directory: Path):
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    match = re.fullmatch(r"n(\d+)-k(\d+)-q(\d+)-e(\d+)_(\d+)-d(\d+)_(\d+)",
                         metadata["parameters"])
    if not match:
        raise ValueError(f"unrecognized parameter id: {metadata['parameters']}")
    n, k, q, eta1, eta2, du, dv = map(int, match.groups())
    return {"n": n, "k": k, "q": q, "eta1": eta1, "eta2": eta2,
            "du": du, "dv": dv, "id": metadata["parameters"]}


def quantized_ratio(value: int, denominator: int, bins: int = 32) -> int:
    if value < 0 or denominator <= 0:
        raise ValueError("normalized norm inputs must be nonnegative")
    return (bins * value) // denominator


def frequency_vector(counts, total):
    if sum(counts) != total:
        raise ValueError(f"histogram mass {sum(counts)} != {total}")
    return ".".join(fraction_text(Fraction(count, total)) for count in counts)


def dot_counts(value: str):
    return [int(item) for item in value.split(".") if item != ""]


def canonicalize(feature: str, value: str, params) -> str:
    n, k, q, du, dv = (params[name] for name in ("n", "k", "q", "du", "dv"))
    if feature == "at_norm_pair":
        match = re.fullmatch(r"A=(\d+)\|t=(\d+)", value)
        if not match:
            raise ValueError(f"bad norm pair: {value}")
        anorm, tnorm = map(int, match.groups())
        return f"A{quantized_ratio(anorm, k * k * n * q * q)}|t{quantized_ratio(tnorm, k * n * q * q)}"
    if feature == "hist_u":
        return frequency_vector(dot_counts(value), k * n)
    if feature == "hist_v":
        return frequency_vector(dot_counts(value), n)
    if feature == "extreme_symbols":
        counts = dot_counts(value)
        if len(counts) != 4:
            raise ValueError(f"bad extreme-symbol feature: {value}")
        return ".".join(fraction_text(x) for x in
                        (Fraction(counts[0], k * n), Fraction(counts[1], k * n),
                         Fraction(counts[2], n), Fraction(counts[3], n)))
    if feature == "entropy_1024":
        values = dot_counts(value)
        return ".".join(fraction_text(Fraction(x, 1024)) for x in values)
    if feature == "decompressed_norms":
        unorm, vnorm = dot_counts(value)
        return f"u{quantized_ratio(unorm, k * n * q * q)}|v{quantized_ratio(vnorm, n * q * q)}"
    if feature == "joint_uv_histogram":
        counts = [[0 for _ in range(1 << dv)] for _ in range(1 << du)]
        for item in value.split(";"):
            if not item:
                continue
            usymbol, vsymbol, count = map(int, item.split(":"))
            counts[usymbol][vsymbol] = count
        flat = [count for row in counts for count in row]
        return frequency_vector(flat, k * n)
    raise ValueError(f"unsupported transfer feature: {feature}")


def load_canonical_law(directory: Path, feature: str):
    params = load_params(directory)
    cells = {}
    with (directory / f"{feature}.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = canonicalize(feature, row["feature_value"], params)
            n, e = int(row["Nz"]), int(row["Ez"])
            old_n, old_e = cells.get(key, (0, 0))
            cells[key] = (old_n + n, old_e + e)
    return params, cells


def selector_for_budget(score_groups, total: int, bits: int):
    target = Fraction(total, 1 << bits)
    cumulative = 0
    for score, mass in sorted(score_groups.items(), reverse=True):
        if cumulative + mass >= target:
            boundary_fraction = (target - cumulative) / mass
            exclude_error = target - cumulative
            include_error = cumulative + mass - target
            include_boundary = include_error <= exclude_error
            return {
                "b": bits,
                "target_p": f"1/{1 << bits}",
                "threshold_score": fraction_text(score),
                "boundary_probability": fraction_text(boundary_fraction),
                "deterministic_include_boundary": include_boundary,
            }
        cumulative += mass
    raise ValueError("budget exceeds law mass")


def train_feature(directory: Path, feature: str, max_bits: int):
    params, cells = load_canonical_law(directory, feature)
    total = sum(n for n, _ in cells.values())
    failures = sum(e for _, e in cells.values())
    delta = Fraction(failures, total)
    scores = {key: Fraction(e, n) / delta if failures else Fraction(0)
              for key, (n, e) in cells.items()}
    groups = {}
    for key, score in scores.items():
        groups[score] = groups.get(score, 0) + cells[key][0]
    return {
        "feature": feature,
        "canonicalization": "dimensionless-v1",
        "training_parameters": params["id"],
        "training_N": str(total),
        "training_E": str(failures),
        "unseen_cell_rule": "reject",
        "scores": {key: fraction_text(value) for key, value in sorted(scores.items())},
        "selectors": [selector_for_budget(groups, total, bits) for bits in range(1, max_bits + 1)],
    }


def train(source: Path, output: Path, max_bits: int = 20):
    models = {}
    for feature, (_, subdirectory) in FEATURES.items():
        models[feature] = train_feature(source / subdirectory, feature, max_bits)
    payload = {
        "schema_version": 1,
        "training_rule": "exact E0 likelihood-ratio score after fixed dimensionless canonicalization",
        "tie_rule": "randomized boundary probability and nearest-mass deterministic inclusion are fixed on E0",
        "models": models,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def oracle_at_mass(cells, target_mass: Fraction):
    ordered = sorted(cells.values(), key=lambda cell: Fraction(cell[1], cell[0]), reverse=True)
    selected_mass = Fraction(0)
    selected_failures = Fraction(0)
    for n, e in ordered:
        if selected_mass + n <= target_mass:
            selected_mass += n
            selected_failures += e
        else:
            fraction = (target_mass - selected_mass) / n
            selected_failures += fraction * e
            selected_mass = target_mass
            break
    return selected_failures


def evaluate_selector(cells, scores, selector, randomized: bool):
    threshold = parse_fraction(selector["threshold_score"])
    boundary = (parse_fraction(selector["boundary_probability"]) if randomized else
                Fraction(int(selector["deterministic_include_boundary"])))
    selected_mass = Fraction(0)
    selected_failures = Fraction(0)
    for key, (n, e) in cells.items():
        if key not in scores:
            continue
        score = scores[key]
        probability = Fraction(int(score > threshold))
        if score == threshold:
            probability = boundary
        selected_mass += probability * n
        selected_failures += probability * e
    return selected_mass, selected_failures


def evaluate_feature(model, directory: Path, feature: str):
    params, cells = load_canonical_law(directory, feature)
    total = sum(n for n, _ in cells.values())
    failures = sum(e for _, e in cells.values())
    delta = Fraction(failures, total)
    scores = {key: parse_fraction(value) for key, value in model["scores"].items()}
    rows = []
    for selector in model["selectors"]:
        row = {"b": selector["b"], "target_p": selector["target_p"]}
        for name, randomized in (("randomized", True), ("deterministic", False)):
            mass, selected_failures = evaluate_selector(cells, scores, selector, randomized)
            p = mass / total
            conditional = selected_failures / mass if mass else Fraction(0)
            amplification = conditional / delta if mass and failures else Fraction(0)
            oracle_failures = oracle_at_mass(cells, mass) if mass else Fraction(0)
            oracle_conditional = oracle_failures / mass if mass else Fraction(0)
            oracle_amplification = oracle_conditional / delta if mass and failures else Fraction(0)
            row[name] = {
                "achieved_p": fraction_text(p),
                "achieved_p_float": float(p),
                "conditional_failure": fraction_text(conditional),
                "conditional_failure_float": float(conditional),
                "amplification": fraction_text(amplification),
                "amplification_float": float(amplification),
                "G_bits": math.log2(float(amplification)) if amplification else None,
                "oracle_amplification_at_achieved_p": float(oracle_amplification),
                "oracle_retention": (float(amplification / oracle_amplification)
                                     if oracle_amplification else None),
            }
        rows.append(row)
    return {"evaluation_parameters": params["id"], "N": str(total), "E": str(failures),
            "delta": fraction_text(delta), "budgets": rows}


def evaluate(model_path: Path, target: Path, output: Path):
    model = json.loads(model_path.read_text(encoding="utf-8"))
    results = {}
    for feature, (_, subdirectory) in FEATURES.items():
        results[feature] = evaluate_feature(model["models"][feature], target / subdirectory, feature)
    payload = {"schema_version": 1, "model": str(model_path), "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--source", type=Path, required=True)
    train_parser.add_argument("--output", type=Path, required=True)
    train_parser.add_argument("--max-bits", type=int, default=20)
    eval_parser = subparsers.add_parser("evaluate")
    eval_parser.add_argument("--model", type=Path, required=True)
    eval_parser.add_argument("--target", type=Path, required=True)
    eval_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        train(args.source, args.output, args.max_bits)
    else:
        evaluate(args.model, args.target, args.output)


if __name__ == "__main__":
    main()
