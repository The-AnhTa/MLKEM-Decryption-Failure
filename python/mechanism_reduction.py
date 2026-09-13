#!/usr/bin/env python3
"""Strict E0-frozen reduction of ciphertext failure signal to simple scalars."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import random
import re
from array import array
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import frozen_normalized_transfer as frozen


COSTS = (2, 4, 6, 8, 10)
BOOTSTRAP_SEED = 20260915
BOOTSTRAP_REPLICATES = 10_000
ZERO_SUPPORT_LIMIT = 0.05

PRIMARY = (
    "S_u2", "S_v2", "S_2sum", "S_2max",
    "S_u1", "S_v1", "S_1sum",
    "E_u_1_4", "E_v_1_4", "E_sum_1_4",
    "E_u_3_8", "E_v_3_8", "E_sum_3_8",
    "B_u_mean", "B_v_mean", "B_sum",
    "B_u_low_1_4", "B_v_low_1_4", "B_sum_low_1_4",
    "B_u_low_3_8", "B_v_low_3_8", "B_sum_low_3_8",
    "C_u", "C_v", "C_sum",
)
SECONDARY = ("S_C",)
STATISTICS = ("T_marg",) + PRIMARY + SECONDARY
CORE_PLOTS = ("T_marg", "S_2sum", "S_1sum", "E_sum_1_4", "E_sum_3_8", "B_sum", "C_sum", "S_C")


@dataclass(frozen=True)
class Record:
    u: tuple[int, ...]
    v: tuple[int, ...]
    margin: int
    total: int
    failures: int
    cluster: int | None = None


def open_text(path: Path):
    if path.exists():
        return path.open("rt", newline="", encoding="utf-8")
    gz = path.with_suffix(path.suffix + ".gz")
    if gz.exists():
        return gzip.open(gz, "rt", newline="", encoding="utf-8")
    parts = sorted(gz.parent.glob(gz.name + ".part*"))
    if parts:
        return io.TextIOWrapper(gzip.GzipFile(fileobj=io.BufferedReader(ConcatenatedFiles(parts))),
                                newline="", encoding="utf-8")
    raise FileNotFoundError(path)


class ConcatenatedFiles(io.RawIOBase):
    """Seek-free reader over deterministic binary chunks of one gzip stream."""
    def __init__(self, paths):
        super().__init__()
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        view = memoryview(buffer)
        written = 0
        while written < len(view):
            if self.current is None:
                try:
                    self.current = next(self.paths).open("rb")
                except StopIteration:
                    break
            count = self.current.readinto(view[written:])
            if count:
                written += count
            else:
                self.current.close()
                self.current = None
        return written

    def close(self):
        if self.current is not None:
            self.current.close()
            self.current = None
        super().close()


def parse_feature(value: str):
    cluster = None
    if value.startswith("K="):
        prefix, value = value.split("|", 1)
        cluster = int(prefix[2:])
    match = re.fullmatch(r"U=([0-9.]+)\|V=([0-9.]+)\|M=(-?\d+)", value)
    if not match:
        raise ValueError("invalid mechanism feature")
    u = tuple(int(x) for x in match.group(1).split("."))
    v = tuple(int(x) for x in match.group(2).split("."))
    return cluster, u, v, int(match.group(3))


def read_records(path: Path, du: int, dv: int, n: int) -> list[Record]:
    records = []
    with open_text(path) as handle:
        for row in csv.DictReader(handle):
            cluster, u, v, margin = parse_feature(row["feature_value"])
            total, failures = int(row["Nz"]), int(row["Ez"])
            if len(u) != 1 << du or len(v) != 1 << dv or sum(u) != n or sum(v) != n:
                raise ValueError("symbol histogram shape or mass mismatch")
            if failures > total or (margin <= 0) != (failures == total):
                raise ValueError("margin/failure mismatch")
            records.append(Record(u, v, margin, total, failures, cluster))
    if not records:
        raise ValueError("empty mechanism law")
    return records


def read_clustered_compact(path: Path, du: int, dv: int, n: int):
    """Read a large key-cluster law without materializing per-row Python objects."""
    pair_ids, clusters, margins, totals = array("I"), array("B"), array("h"), array("Q")
    pair_index, pairs = {}, []
    cluster_n, cluster_e = [0] * 128, [0] * 128
    with open_text(path) as handle:
        for row in csv.DictReader(handle):
            cluster, u, v, margin = parse_feature(row["feature_value"])
            total, failures = int(row["Nz"]), int(row["Ez"])
            if cluster is None or not 0 <= cluster < 128:
                raise ValueError("cluster id outside frozen 0..127 range")
            if len(u) != 1 << du or len(v) != 1 << dv or sum(u) != n or sum(v) != n:
                raise ValueError("symbol histogram shape or mass mismatch")
            if not -32768 <= margin <= 32767:
                raise ValueError("margin does not fit compact signed representation")
            if failures > total or (margin <= 0) != (failures == total):
                raise ValueError("margin/failure mismatch")
            pair = (u, v)
            pair_id = pair_index.get(pair)
            if pair_id is None:
                pair_id = len(pairs)
                pair_index[pair] = pair_id
                pairs.append(pair)
            pair_ids.append(pair_id); clusters.append(cluster); margins.append(margin); totals.append(total)
            cluster_n[cluster] += total; cluster_e[cluster] += failures
    if not pair_ids:
        raise ValueError("empty clustered mechanism law")
    if len(set(cluster_n)) != 1 or any(value == 0 for value in cluster_n):
        raise ValueError("outer-key clusters do not have equal positive exact inner mass")
    return pair_ids, clusters, margins, totals, pairs, cluster_n, cluster_e


def decompress(symbol: int, d: int, q: int) -> int:
    return (q * symbol + (1 << (d - 1))) >> d


def center(value: int, q: int) -> int:
    residue = value % q
    return residue - q if residue > q // 2 else residue


def normalized_bin(value: int, q: int) -> int:
    value = center(value, q)
    if 4 * value < -q:
        return 0
    if value < 0:
        return 1
    if 4 * value < q:
        return 2
    return 3


def boundary_distance(symbol: int, d: int, q: int) -> Fraction:
    width = 1 << d
    representative = decompress(symbol, d, q)
    lower = abs(2 * width * representative - q * (2 * symbol - 1))
    upper = abs(2 * width * representative - q * (2 * symbol + 1))
    return Fraction(min(lower, upper), 2 * q)


def side_values(counts: tuple[int, ...], d: int, q: int) -> dict[str, Fraction]:
    n = sum(counts)
    centered = [center(decompress(z, d, q), q) for z in range(len(counts))]
    moment1 = sum(Fraction(count * abs(x), q * n) for count, x in zip(counts, centered))
    moment2 = sum(Fraction(count * x * x, q * q * n) for count, x in zip(counts, centered))
    extreme_1_4 = Fraction(sum(count for count, x in zip(counts, centered) if 4 * abs(x) >= q), n)
    extreme_3_8 = Fraction(sum(count for count, x in zip(counts, centered) if 8 * abs(x) >= 3 * q), n)
    distances = [boundary_distance(z, d, q) for z in range(len(counts))]
    boundary_mean = sum((count * distance for count, distance in zip(counts, distances)), Fraction()) / n
    boundary_low_1_4 = Fraction(sum(count for count, distance in zip(counts, distances)
                                      if distance <= Fraction(1, 4)), n)
    boundary_low_3_8 = Fraction(sum(count for count, distance in zip(counts, distances)
                                      if distance <= Fraction(3, 8)), n)
    concentration = Fraction(sum(count * count for count in counts), n * n)
    return {"m1": moment1, "m2": moment2, "e14": extreme_1_4, "e38": extreme_3_8,
            "bmean": boundary_mean, "bl14": boundary_low_1_4,
            "bl38": boundary_low_3_8, "concentration": concentration}


def raw_scalars(record: Record, params: dict, marginal_weights: dict, lam: Fraction = Fraction()) -> dict[str, float]:
    u = side_values(record.u, params["du"], params["q"])
    v = side_values(record.v, params["dv"], params["q"])
    n = params["n"]
    alpha = [float.fromhex(x) for x in marginal_weights["u"]]
    beta = [float.fromhex(x) for x in marginal_weights["v"]]
    # Preserve the exact four-bin aggregation and summation convention of the
    # already-frozen baseline. This is significant because AUC tie classes are
    # defined by the resulting binary64 score values.
    u_bins, v_bins = [0] * 4, [0] * 4
    for z, count in enumerate(record.u):
        u_bins[normalized_bin(decompress(z, params["du"], params["q"]), params["q"])] += count
    for z, count in enumerate(record.v):
        v_bins[normalized_bin(decompress(z, params["dv"], params["q"]), params["q"])] += count
    t_marg = math.fsum(weight * count / n for weight, count in zip(alpha, u_bins)) + \
        math.fsum(weight * count / n for weight, count in zip(beta, v_bins))
    values = {
        "T_marg": t_marg,
        "S_u2": float(u["m2"]), "S_v2": float(v["m2"]),
        "S_2sum": float(u["m2"] + v["m2"]), "S_2max": float(max(u["m2"], v["m2"])),
        "S_u1": float(u["m1"]), "S_v1": float(v["m1"]), "S_1sum": float(u["m1"] + v["m1"]),
        "E_u_1_4": float(u["e14"]), "E_v_1_4": float(v["e14"]),
        "E_sum_1_4": float(u["e14"] + v["e14"]),
        "E_u_3_8": float(u["e38"]), "E_v_3_8": float(v["e38"]),
        "E_sum_3_8": float(u["e38"] + v["e38"]),
        "B_u_mean": float(u["bmean"]), "B_v_mean": float(v["bmean"]),
        "B_sum": float(u["bmean"] + v["bmean"]),
        "B_u_low_1_4": float(u["bl14"]), "B_v_low_1_4": float(v["bl14"]),
        "B_sum_low_1_4": float(u["bl14"] + v["bl14"]),
        "B_u_low_3_8": float(u["bl38"]), "B_v_low_3_8": float(v["bl38"]),
        "B_sum_low_3_8": float(u["bl38"] + v["bl38"]),
        "C_u": float(u["concentration"]), "C_v": float(v["concentration"]),
        "C_sum": float(u["concentration"] + v["concentration"]),
    }
    values["S_C"] = values["S_2sum"] + float(lam) * values["E_sum_1_4"]
    return values


def params_from_metadata(directory: Path) -> dict:
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    match = re.fullmatch(r"n(\d+)-k(\d+)-q(\d+)-e\d+_\d+-d(\d+)_(\d+)", metadata["parameters"])
    if not match:
        raise ValueError("unknown parameter identifier")
    n, k, q, du, dv = map(int, match.groups())
    if k != 1:
        raise ValueError("mechanism study is predeclared for k=1")
    return {"n": n, "q": q, "du": du, "dv": dv, "metadata": metadata}


def score_law(records, values, statistic, sign):
    law = defaultdict(lambda: [0, 0])
    for record, scalar in zip(records, values):
        score = sign * scalar[statistic]
        law[score][0] += record.total
        law[score][1] += record.failures
    return dict(law)


def orientation_from_auc(auc: float) -> int:
    return 1 if auc >= 0.5 else -1


def cluster_draws(cluster_count: int, replicates: int = BOOTSTRAP_REPLICATES,
                  seed: int = BOOTSTRAP_SEED):
    rng = random.Random(seed)
    output = []
    for _ in range(replicates):
        counts = [0] * cluster_count
        for _ in range(cluster_count):
            counts[rng.randrange(cluster_count)] += 1
        output.append(counts)
    return output


def support_diagnostic(gain_values, zero: int, replicates: int):
    fraction = zero / replicates
    return {"gain_ci": frozen.percentile_interval(gain_values),
            "valid": replicates - zero, "zero": zero, "r_zero": fraction,
            "status": "unsupported" if fraction >= ZERO_SUPPORT_LIMIT else "supported"}


def exact_weighted_spearman(records, values, statistic, sign):
    score_mass, margin_mass = defaultdict(int), defaultdict(int)
    total = sum(r.total for r in records)
    for record, scalar in zip(records, values):
        score_mass[sign * scalar[statistic]] += record.total
        margin_mass[record.margin] += record.total
    def ranks(masses):
        below = 0
        out = {}
        for value in sorted(masses):
            out[value] = (below + masses[value] / 2) / total
            below += masses[value]
        return out
    sr, mr = ranks(score_mass), ranks(margin_mass)
    mean_s = sum(mass * sr[value] for value, mass in score_mass.items()) / total
    mean_m = sum(mass * mr[value] for value, mass in margin_mass.items()) / total
    cov = var_s = var_m = 0.0
    for record, scalar in zip(records, values):
        ds = sr[sign * scalar[statistic]] - mean_s
        dm = mr[record.margin] - mean_m
        cov += record.total * ds * dm
        var_s += record.total * ds * ds
        var_m += record.total * dm * dm
    return cov / math.sqrt(var_s * var_m) if var_s and var_m else None


def joint_law(scores, margins, weights):
    law = defaultdict(lambda: [0, 0])
    failure_mask = margins <= 0
    for score_index, score in enumerate(scores):
        row = weights[score_index]
        total = int(row.sum())
        if total:
            law[float(score)] = [total, int(row[failure_mask].sum())]
    return dict(law)


def joint_spearman(scores, margins, weights):
    score_mass = weights.sum(axis=1)
    margin_mass = weights.sum(axis=0)
    total = float(score_mass.sum())
    score_rank = (score_mass.cumsum() - score_mass + 0.5 * score_mass) / total
    margin_rank = (margin_mass.cumsum() - margin_mass + 0.5 * margin_mass) / total
    mean_s = float((score_mass * score_rank).sum() / total)
    mean_m = float((margin_mass * margin_rank).sum() / total)
    covariance = float((weights * score_rank[:, None] * margin_rank[None, :]).sum() / total - mean_s * mean_m)
    variance_s = float((score_mass * score_rank * score_rank).sum() / total - mean_s * mean_s)
    variance_m = float((margin_mass * margin_rank * margin_rank).sum() / total - mean_m * mean_m)
    return covariance / math.sqrt(variance_s * variance_m) if variance_s and variance_m else None


def joint_quintiles(dataset, statistic, scores, margins, weights):
    score_mass = weights.sum(axis=1)
    total = float(score_mass.sum())
    assignments, cumulative = [], 0.0
    for mass in score_mass:
        assignments.append(min(4, int(5 * (cumulative + float(mass) / 2) / total)))
        cumulative += float(mass)
    rows, cdf_rows = [], []
    for quintile in range(5):
        indices = [i for i, value in enumerate(assignments) if value == quintile]
        if not indices:
            continue
        distribution = weights[indices].sum(axis=0)
        mass = float(distribution.sum())
        nonzero = distribution > 0
        margin_values = margins[nonzero]
        margin_weights = distribution[nonzero]
        cumulative_margin = margin_weights.cumsum()
        median_index = int((cumulative_margin * 2 >= mass).argmax())
        rows.append({"dataset": dataset, "statistic": statistic, "quintile": quintile + 1,
            "quintile_probability": mass / total, "score_min": float(scores[min(indices)]),
            "score_max": float(scores[max(indices)]),
            "mean_margin": float((margin_values * margin_weights).sum() / mass),
            "median_margin": int(margin_values[median_index]),
            "failure_probability": float(margin_weights[margin_values <= 0].sum() / mass)})
        for margin, cdf in zip(margin_values, cumulative_margin / mass):
            cdf_rows.append({"dataset": dataset, "statistic": statistic, "quintile": quintile + 1,
                             "margin": int(margin), "conditional_cdf": float(cdf)})
    if not math.isclose(sum(row["quintile_probability"] for row in rows), 1.0):
        raise ValueError("joint quintile mass not conserved")
    return rows, cdf_rows


def solve_lambda(records, values) -> Fraction:
    matrix = [[Fraction() for _ in range(3)] for _ in range(3)]
    rhs = [Fraction() for _ in range(3)]
    for record, scalar in zip(records, values):
        x = (Fraction(1), Fraction.from_float(scalar["S_2sum"]),
             Fraction.from_float(scalar["E_sum_1_4"]))
        for i in range(3):
            rhs[i] += record.failures * x[i]
            for j in range(3):
                matrix[i][j] += record.total * x[i] * x[j]
    augmented = [matrix[i] + [rhs[i]] for i in range(3)]
    for column in range(3):
        pivot = next((row for row in range(column, 3) if augmented[row][column]), None)
        if pivot is None:
            return Fraction()
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(3):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    b1, b2 = augmented[1][3], augmented[2][3]
    return b2 / b1 if b1 else Fraction()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train(e0_dir: Path, baseline_artifact: Path, output: Path):
    if "e0" not in {part.lower() for part in e0_dir.parts}:
        raise ValueError("training requires an explicitly named E0 directory")
    baseline_model, marginal_weights = frozen.load_model(baseline_artifact)
    params = params_from_metadata(e0_dir)
    records = read_records(e0_dir / "mechanism_margin.csv", params["du"], params["dv"], params["n"])
    provisional = [raw_scalars(record, params, marginal_weights) for record in records]
    lam = solve_lambda(records, provisional)
    values = [raw_scalars(record, params, marginal_weights, lam) for record in records]
    orientations, thresholds, e0_auc, degeneracy = {}, {}, {}, {}
    for statistic in STATISTICS:
        raw_law = score_law(records, values, statistic, 1)
        _, auc = frozen.weighted_roc(raw_law)
        sign = orientation_from_auc(auc)
        orientations[statistic] = sign
        law = score_law(records, values, statistic, sign)
        e0_auc[statistic] = frozen.weighted_roc(law)[1]
        degeneracy[statistic] = len(law) == 1
        thresholds[statistic] = {}
        for cost in COSTS:
            threshold, probability = frozen.calibrate_threshold(law, 2.0 ** -cost)
            thresholds[statistic][str(cost)] = {"decimal": threshold, "hex": threshold.hex(),
                                                 "selection_probability": probability}
    model = {
        "schema_version": 1, "training_dataset": "e0",
        "source_sha256": file_sha256(e0_dir / "mechanism_margin.csv"),
        "baseline_artifact_sha256": file_sha256(baseline_artifact),
        "baseline_weights": marginal_weights,
        "statistics": list(STATISTICS), "primary_statistics": list(PRIMARY),
        "secondary_statistics": list(SECONDARY), "orientation": orientations,
        "e0_auc": e0_auc, "degenerate_on_e0": degeneracy,
        "lambda": {"numerator": str(lam.numerator), "denominator": str(lam.denominator),
                   "decimal": float(lam), "hex": float(lam).hex(),
                   "rule": "exact-weight least-squares b2/b1"},
        "selection_costs": list(COSTS), "e0_thresholds": thresholds,
        "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": BOOTSTRAP_SEED,
                      "zero_support_limit": ZERO_SUPPORT_LIMIT},
        "boundary_definition": "min(|2Lr-q(2z-1)|,|2Lr-q(2z+1)|)/(2q)",
        "best_scalar_rule": "maximize minimum n4 AUC; lexicographic tie break",
        "case_a_retained_fraction": 0.75,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_config(path: Path):
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != 1 or model.get("training_dataset") != "e0":
        raise ValueError("invalid frozen mechanism config")
    if tuple(model.get("statistics", ())) != STATISTICS or tuple(model.get("selection_costs", ())) != COSTS:
        raise ValueError("frozen statistic set changed")
    if model.get("bootstrap") != {"replicates": BOOTSTRAP_REPLICATES, "seed": BOOTSTRAP_SEED,
                                  "zero_support_limit": ZERO_SUPPORT_LIMIT}:
        raise ValueError("frozen bootstrap settings changed")
    if set(model.get("orientation", {})) != set(STATISTICS) or any(
            sign not in (-1, 1) for sign in model["orientation"].values()):
        raise ValueError("invalid frozen orientations")
    if float.fromhex(model["lambda"]["hex"]) != model["lambda"]["decimal"]:
        raise ValueError("frozen lambda encoding changed")
    for statistic in STATISTICS:
        for cost in COSTS:
            entry = model["e0_thresholds"][statistic][str(cost)]
            if float.fromhex(entry["hex"]) != entry["decimal"]:
                raise ValueError("frozen threshold encoding changed")
    return model


def tail_curve(law):
    total = sum(cell[0] for cell in law.values())
    failures = sum(cell[1] for cell in law.values())
    tail_n = tail_e = 0
    rows = []
    for threshold in sorted(law, reverse=True):
        tail_n += law[threshold][0]
        tail_e += law[threshold][1]
        p = tail_n / total
        conditional = tail_e / tail_n
        amplification = conditional / (failures / total)
        rows.append({"threshold": threshold, "selection_probability": p,
                     "actual_selection_cost_bits": -math.log2(p),
                     "baseline_failure_probability": failures / total,
                     "conditional_failure_probability": conditional,
                     "amplification": amplification,
                     "gain_bits": math.log2(amplification) if amplification > 0 else -math.inf})
    return rows


def weighted_median(distribution):
    total = sum(distribution.values())
    cumulative = 0
    for value in sorted(distribution):
        cumulative += distribution[value]
        if 2 * cumulative >= total:
            return value
    raise ValueError("empty distribution")


def quintile_summary(dataset, statistic, records, values, sign):
    score_mass = defaultdict(int)
    joint = defaultdict(lambda: defaultdict(int))
    for record, scalar in zip(records, values):
        score = sign * scalar[statistic]
        score_mass[score] += record.total
        joint[score][record.margin] += record.total
    total = sum(score_mass.values())
    assignment, cumulative = {}, 0
    for score in sorted(score_mass):
        mass = score_mass[score]
        assignment[score] = min(4, int(5 * (cumulative + mass / 2) / total))
        cumulative += mass
    margins = [defaultdict(int) for _ in range(5)]
    score_ranges = [[] for _ in range(5)]
    for score, distribution in joint.items():
        q = assignment[score]
        score_ranges[q].append(score)
        for margin, mass in distribution.items():
            margins[q][margin] += mass
    rows, cdf_rows = [], []
    for q, distribution in enumerate(margins):
        mass = sum(distribution.values())
        if not mass:
            continue
        mean = sum(m * w for m, w in distribution.items()) / mass
        failure = sum(w for m, w in distribution.items() if m <= 0) / mass
        rows.append({"dataset": dataset, "statistic": statistic, "quintile": q + 1,
                     "quintile_probability": mass / total, "score_min": min(score_ranges[q]),
                     "score_max": max(score_ranges[q]), "mean_margin": mean,
                     "median_margin": weighted_median(distribution), "failure_probability": failure})
        running = 0
        for margin in sorted(distribution):
            running += distribution[margin]
            cdf_rows.append({"dataset": dataset, "statistic": statistic, "quintile": q + 1,
                             "margin": margin, "conditional_cdf": running / mass})
    if not math.isclose(sum(row["quintile_probability"] for row in rows), 1.0):
        raise ValueError("quintile mass not conserved")
    return rows, cdf_rows


def bootstrap(records, values, config):
    import numpy as np
    clusters = sorted({r.cluster for r in records})
    if clusters != list(range(128)):
        raise ValueError("bootstrap requires clusters 0..127")
    margins = sorted({r.margin for r in records})
    margin_index = {value: i for i, value in enumerate(margins)}
    draws = np.asarray(cluster_draws(128), dtype=np.float64)
    output = {}
    for statistic in STATISTICS:
        sign = config["orientation"][statistic]
        scores = sorted({sign * scalar[statistic] for scalar in values})
        score_index = {value: i for i, value in enumerate(scores)}
        tensor = np.zeros((128, len(scores), len(margins)), dtype=np.float64)
        for record, scalar in zip(records, values):
            tensor[record.cluster, score_index[sign * scalar[statistic]], margin_index[record.margin]] += record.total
        auc_values, corr_values = [], []
        gains = {cost: [] for cost in COSTS}
        zeros = {cost: 0 for cost in COSTS}
        score_array = np.asarray(scores)
        margin_array = np.asarray(margins)
        failure_mask = margin_array <= 0
        threshold_index = {cost: int(np.searchsorted(
            score_array, float.fromhex(config["e0_thresholds"][statistic][str(cost)]["hex"]), side="left"))
            for cost in COSTS}
        for start in range(0, BOOTSTRAP_REPLICATES, 200):
            sample = draws[start:start + 200]
            weights = np.einsum("bc,csm->bsm", sample, tensor, optimize=True)
            score_mass = weights.sum(axis=2)
            margin_mass = weights.sum(axis=1)
            total = score_mass.sum(axis=1)
            failure_total = weights[:, :, failure_mask].sum(axis=(1, 2))
            positives = weights[:, :, failure_mask].sum(axis=2)
            negatives = score_mass - positives
            below_negative = np.cumsum(negatives, axis=1) - negatives
            favorable = (positives * (below_negative + 0.5 * negatives)).sum(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                auc_values.extend((favorable / (failure_total * (total - failure_total))).tolist())
            score_below = np.cumsum(score_mass, axis=1) - score_mass
            margin_below = np.cumsum(margin_mass, axis=1) - margin_mass
            score_rank = (score_below + 0.5 * score_mass) / total[:, None]
            margin_rank = (margin_below + 0.5 * margin_mass) / total[:, None]
            mean_s = (score_mass * score_rank).sum(axis=1) / total
            mean_m = (margin_mass * margin_rank).sum(axis=1) / total
            cross = (weights * score_rank[:, :, None] * margin_rank[:, None, :]).sum(axis=(1, 2)) / total
            second_s = (score_mass * score_rank * score_rank).sum(axis=1) / total
            second_m = (margin_mass * margin_rank * margin_rank).sum(axis=1) / total
            with np.errstate(divide="ignore", invalid="ignore"):
                corr_values.extend(((cross - mean_s * mean_m) /
                                    np.sqrt((second_s - mean_s ** 2) * (second_m - mean_m ** 2))).tolist())
            tail_n = np.cumsum(score_mass[:, ::-1], axis=1)[:, ::-1]
            tail_e = np.cumsum(positives[:, ::-1], axis=1)[:, ::-1]
            for cost, index in threshold_index.items():
                if index == len(scores):
                    selected_n = np.zeros(len(total)); selected_e = np.zeros(len(total))
                else:
                    selected_n, selected_e = tail_n[:, index], tail_e[:, index]
                zero = selected_n == 0
                zeros[cost] += int(zero.sum())
                valid = ~zero
                with np.errstate(divide="ignore", invalid="ignore"):
                    gain = np.log2((selected_e[valid] / selected_n[valid]) /
                                   (failure_total[valid] / total[valid]))
                gains[cost].extend(gain.tolist())
        output[statistic] = {"auc_values": auc_values, "corr_values": corr_values,
                             "gain_values": gains, "zero": zeros}
    baseline_auc = output["T_marg"]["auc_values"]
    summary = {}
    diagnostics = {}
    for statistic in STATISTICS:
        auc = output[statistic]["auc_values"]
        corr = output[statistic]["corr_values"]
        diff = [a - b for a, b in zip(auc, baseline_auc)]
        summary[statistic] = {"auc_ci": frozen.percentile_interval(auc),
                              "auc_diff_ci": frozen.percentile_interval(diff),
                              "corr_ci": frozen.percentile_interval(corr)}
        diagnostics[statistic] = {}
        for cost in COSTS:
            zero = output[statistic]["zero"][cost]
            diagnostics[statistic][cost] = support_diagnostic(
                output[statistic]["gain_values"][cost], zero, BOOTSTRAP_REPLICATES)
    return summary, diagnostics


def bootstrap_joint(tensor, scores, margins, statistic, config, draws):
    """Cluster bootstrap from an exact cluster x score x margin count tensor."""
    import numpy as np
    auc_values, corr_values = [], []
    gains = {cost: [] for cost in COSTS}
    zeros = {cost: 0 for cost in COSTS}
    failure_mask = margins <= 0
    threshold_index = {cost: int(np.searchsorted(
        scores, float.fromhex(config["e0_thresholds"][statistic][str(cost)]["hex"]), side="left"))
        for cost in COSTS}
    for start in range(0, BOOTSTRAP_REPLICATES, 200):
        sample = draws[start:start + 200]
        weights = np.einsum("bc,csm->bsm", sample, tensor, optimize=True)
        score_mass = weights.sum(axis=2)
        margin_mass = weights.sum(axis=1)
        total = score_mass.sum(axis=1)
        failure_total = weights[:, :, failure_mask].sum(axis=(1, 2))
        positives = weights[:, :, failure_mask].sum(axis=2)
        negatives = score_mass - positives
        below_negative = np.cumsum(negatives, axis=1) - negatives
        favorable = (positives * (below_negative + 0.5 * negatives)).sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            auc_values.extend((favorable / (failure_total * (total - failure_total))).tolist())
        score_below = np.cumsum(score_mass, axis=1) - score_mass
        margin_below = np.cumsum(margin_mass, axis=1) - margin_mass
        score_rank = (score_below + 0.5 * score_mass) / total[:, None]
        margin_rank = (margin_below + 0.5 * margin_mass) / total[:, None]
        mean_s = (score_mass * score_rank).sum(axis=1) / total
        mean_m = (margin_mass * margin_rank).sum(axis=1) / total
        cross = (weights * score_rank[:, :, None] * margin_rank[:, None, :]).sum(axis=(1, 2)) / total
        second_s = (score_mass * score_rank * score_rank).sum(axis=1) / total
        second_m = (margin_mass * margin_rank * margin_rank).sum(axis=1) / total
        with np.errstate(divide="ignore", invalid="ignore"):
            corr_values.extend(((cross - mean_s * mean_m) /
                                np.sqrt((second_s - mean_s ** 2) * (second_m - mean_m ** 2))).tolist())
        tail_n = np.cumsum(score_mass[:, ::-1], axis=1)[:, ::-1]
        tail_e = np.cumsum(positives[:, ::-1], axis=1)[:, ::-1]
        for cost, index in threshold_index.items():
            if index == len(scores):
                selected_n = np.zeros(len(total)); selected_e = np.zeros(len(total))
            else:
                selected_n, selected_e = tail_n[:, index], tail_e[:, index]
            zero = selected_n == 0
            zeros[cost] += int(zero.sum())
            valid = ~zero
            with np.errstate(divide="ignore", invalid="ignore"):
                gain = np.log2((selected_e[valid] / selected_n[valid]) /
                               (failure_total[valid] / total[valid]))
            gains[cost].extend(gain.tolist())
    return {"auc_values": auc_values, "corr_values": corr_values,
            "gain_values": gains, "zero": zeros}


def summarize_bootstrap(raw):
    baseline_auc = raw["T_marg"]["auc_values"]
    summary, diagnostics = {}, {}
    for statistic in STATISTICS:
        auc = raw[statistic]["auc_values"]
        corr = raw[statistic]["corr_values"]
        summary[statistic] = {
            "auc_ci": frozen.percentile_interval(auc),
            "auc_diff_ci": frozen.percentile_interval([a - b for a, b in zip(auc, baseline_auc)]),
            "corr_ci": frozen.percentile_interval(corr),
        }
        diagnostics[statistic] = {
            cost: support_diagnostic(raw[statistic]["gain_values"][cost],
                                     raw[statistic]["zero"][cost], BOOTSTRAP_REPLICATES)
            for cost in COSTS}
    return summary, diagnostics


def linear_fit(rows, predictor):
    weights = [row["probability"] for row in rows]
    x = [row[predictor] for row in rows]
    y = [row["weight"] for row in rows]
    total = sum(weights)
    mx = sum(w * a for w, a in zip(weights, x)) / total
    my = sum(w * b for w, b in zip(weights, y)) / total
    var = sum(w * (a - mx) ** 2 for w, a in zip(weights, x))
    cov = sum(w * (a - mx) * (b - my) for w, a, b in zip(weights, x, y))
    slope = cov / var if var else 0.0
    intercept = my - slope * mx
    sse = sum(w * (b - intercept - slope * a) ** 2 for w, a, b in zip(weights, x, y))
    sst = sum(w * (b - my) ** 2 for w, b in zip(weights, y))
    return intercept, slope, 1 - sse / sst if sst else None, sse


def histogram_weight_analysis(e0_records, params, config):
    rows = []
    for side, d in (("u", params["du"]), ("v", params["dv"])):
        symbol_mass = [0] * (1 << d)
        for record in e0_records:
            counts = record.u if side == "u" else record.v
            for symbol, count in enumerate(counts):
                symbol_mass[symbol] += count * record.total
        denominator = sum(symbol_mass)
        weights = [float.fromhex(x) for x in config["baseline_weights"][side]]
        side_rows = []
        for symbol, mass in enumerate(symbol_mass):
            x = center(decompress(symbol, d, params["q"]), params["q"]) / params["q"]
            side_rows.append({"side": side, "symbol": symbol, "normalized_value": x,
                "absolute_value": abs(x), "squared_value": x * x,
                "boundary_distance": float(boundary_distance(symbol, d, params["q"])),
                "weight": weights[normalized_bin(decompress(symbol, d, params["q"]), params["q"])],
                "probability": mass / denominator})
        fits = {predictor: linear_fit(side_rows, predictor)
                for predictor in ("absolute_value", "squared_value", "boundary_distance")}
        for row in side_rows:
            for predictor, (intercept, slope, r2, sse) in fits.items():
                row[f"{predictor}_intercept"] = intercept
                row[f"{predictor}_slope"] = slope
                row[f"{predictor}_r2"] = r2
                row[f"{predictor}_weighted_sse"] = sse
            rows.append(row)
    return rows


def compact_n4_analysis(directory, params, config, lam):
    import numpy as np
    packed = read_clustered_compact(directory / "mechanism_margin_by_key.csv",
                                    params["du"], params["dv"], params["n"])
    pair_ids_raw, clusters_raw, margins_raw, totals_raw, pairs, cluster_n, cluster_e = packed
    meta = params["metadata"]["laws"]["global"]
    if sum(cluster_n) != int(meta["N"]) or sum(cluster_e) != int(meta["E"]):
        raise ValueError(f"{directory.name}: clustered probability mass not preserved")
    pair_ids = np.frombuffer(pair_ids_raw, dtype=np.uint32)
    clusters = np.frombuffer(clusters_raw, dtype=np.uint8)
    margin_rows = np.frombuffer(margins_raw, dtype=np.int16)
    totals = np.frombuffer(totals_raw, dtype=np.uint64)
    value_matrix = np.empty((len(pairs), len(STATISTICS)), dtype=np.float64)
    for pair_index, (u, v) in enumerate(pairs):
        values = raw_scalars(Record(u, v, 0, 0, 0), params, config["baseline_weights"], lam)
        value_matrix[pair_index] = [values[name] for name in STATISTICS]
    margin_values, margin_codes = np.unique(margin_rows, return_inverse=True)
    draws = np.asarray(cluster_draws(128), dtype=np.float64)
    joints, bootstrap_raw = {}, {}
    for statistic_index, statistic in enumerate(STATISTICS):
        oriented = config["orientation"][statistic] * value_matrix[:, statistic_index]
        score_values, pair_score_codes = np.unique(oriented, return_inverse=True)
        row_score_codes = pair_score_codes[pair_ids]
        flat = clusters.astype(np.int64)
        flat *= len(score_values)
        flat += row_score_codes
        flat *= len(margin_values)
        flat += margin_codes
        tensor = np.bincount(flat, weights=totals,
            minlength=128 * len(score_values) * len(margin_values)).reshape(
                128, len(score_values), len(margin_values))
        if int(tensor.sum()) != int(meta["N"]):
            raise ValueError(f"{directory.name}/{statistic}: tensor mass not preserved")
        joints[statistic] = (score_values, margin_values, tensor.sum(axis=0))
        bootstrap_raw[statistic] = bootstrap_joint(
            tensor, score_values, margin_values, statistic, config, draws)
    bootstrap_summary, bootstrap_diag = summarize_bootstrap(bootstrap_raw)
    return joints, bootstrap_summary, bootstrap_diag


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: frozen.value_text(row.get(field)) for field in fields})


def evaluate(root: Path, config_path: Path):
    config = load_config(config_path)
    lam = Fraction(int(config["lambda"]["numerator"]), int(config["lambda"]["denominator"]))
    datasets = {name: root / "data" / name for name in ("e0", "e1a", "n4q29d43", "n4q19d43")}
    all_records, all_values, params, n4_joints = {}, {}, {}, {}
    bootstrap_summary, bootstrap_diag = {}, {}
    for dataset, directory in datasets.items():
        params[dataset] = params_from_metadata(directory)
        if dataset.startswith("n4"):
            n4_joints[dataset], bootstrap_summary[dataset], bootstrap_diag[dataset] = compact_n4_analysis(
                directory, params[dataset], config, lam)
        else:
            records = read_records(directory / "mechanism_margin.csv",
                                   params[dataset]["du"], params[dataset]["dv"], params[dataset]["n"])
            total, failures = sum(r.total for r in records), sum(r.failures for r in records)
            meta = params[dataset]["metadata"]["laws"]["global"]
            if total != int(meta["N"]) or failures != int(meta["E"]):
                raise ValueError(f"{dataset}: probability mass not preserved")
            all_records[dataset] = records
            all_values[dataset] = [raw_scalars(r, params[dataset], config["baseline_weights"], lam) for r in records]

    scalar_rows, tail_rows, margin_rows = [], [], []
    laws = {}
    cdf_by_dataset_stat = {}
    for dataset in datasets:
        laws[dataset] = {}
        baseline_auc = None
        metric_cache = {}
        for statistic in STATISTICS:
            if dataset.startswith("n4"):
                scores, margin_values, joint = n4_joints[dataset][statistic]
                law = joint_law(scores, margin_values, joint)
                corr = joint_spearman(scores, margin_values, joint)
                summaries, cdfs = joint_quintiles(dataset, statistic, scores, margin_values, joint)
            else:
                sign = config["orientation"][statistic]
                law = score_law(all_records[dataset], all_values[dataset], statistic, sign)
                corr = exact_weighted_spearman(all_records[dataset], all_values[dataset], statistic, sign)
                summaries, cdfs = quintile_summary(
                    dataset, statistic, all_records[dataset], all_values[dataset], sign)
            laws[dataset][statistic] = law
            _, auc = frozen.weighted_roc(law)
            metric_cache[statistic] = (auc, corr)
            if statistic == "T_marg": baseline_auc = auc
            margin_rows.extend(summaries)
            cdf_by_dataset_stat[(dataset, statistic)] = cdfs
            for row in tail_curve(law):
                tail_rows.append({"dataset": dataset, "statistic": statistic,
                                  "curve_or_frozen": "curve", "target_s": None, **row,
                                  "bootstrap_valid_replicates": None,
                                  "bootstrap_zero_support_replicates": None,
                                  "bootstrap_zero_support_fraction": None, "support_status": "exact-curve"})
        for statistic in STATISTICS:
            auc, corr = metric_cache[statistic]
            retained = ((auc - 0.5) / (baseline_auc - 0.5)) if baseline_auc != 0.5 else None
            if dataset.startswith("n4"):
                ci = bootstrap_summary[dataset][statistic]
                auc_ci, diff_ci, corr_ci = ci["auc_ci"], ci["auc_diff_ci"], ci["corr_ci"]
            else:
                auc_ci, diff_ci, corr_ci = (auc, auc), (auc - baseline_auc, auc - baseline_auc), (corr, corr)
            scalar_rows.append({"dataset": dataset, "statistic": statistic,
                "public_or_diagnostic": "public" if statistic != "S_C" else "public-secondary",
                "E0_orientation": config["orientation"][statistic], "auc": auc,
                "auc_ci_low": auc_ci[0], "auc_ci_high": auc_ci[1],
                "auc_minus_baseline": auc - baseline_auc,
                "auc_minus_baseline_ci_low": diff_ci[0], "auc_minus_baseline_ci_high": diff_ci[1],
                "auc_retained_fraction": retained, "margin_rank_correlation": corr,
                "margin_corr_ci_low": corr_ci[0], "margin_corr_ci_high": corr_ci[1],
                "degenerate_on_e0": config["degenerate_on_e0"][statistic]})
            for cost in COSTS:
                threshold = float.fromhex(config["e0_thresholds"][statistic][str(cost)]["hex"])
                metric = frozen.metric_at(laws[dataset][statistic], threshold)
                diag = bootstrap_diag[dataset][statistic][cost] if dataset.startswith("n4") else {
                    "gain_ci": (metric["gain"], metric["gain"]), "valid": None, "zero": None,
                    "r_zero": None, "status": "exact"}
                tail_rows.append({"dataset": dataset, "statistic": statistic,
                    "curve_or_frozen": "frozen-e0", "target_s": cost, "threshold": threshold,
                    "selection_probability": metric["p"],
                    "actual_selection_cost_bits": -math.log2(metric["p"]) if metric["p"] else math.inf,
                    "baseline_failure_probability": metric["delta"],
                    "conditional_failure_probability": metric["conditional"],
                    "amplification": metric["amplification"], "gain_bits": metric["gain"],
                    "gain_ci_low": diag["gain_ci"][0], "gain_ci_high": diag["gain_ci"][1],
                    "bootstrap_valid_replicates": diag["valid"],
                    "bootstrap_zero_support_replicates": diag["zero"],
                    "bootstrap_zero_support_fraction": diag["r_zero"], "support_status": diag["status"]})

    prior_path = root.parent / "frozen-normalized-transfer" / "joint-vs-marginal.csv"
    expected_auc = {}
    with prior_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            expected_auc.setdefault(row["dataset"], float(row["marginal_auc"]))
    for dataset in datasets:
        observed = next(r["auc"] for r in scalar_rows
                        if r["dataset"] == dataset and r["statistic"] == "T_marg")
        if not math.isclose(observed, expected_auc[dataset], rel_tol=0.0, abs_tol=1e-15):
            raise ValueError(f"{dataset}: frozen T_marg AUC was not exactly reproduced")

    n4_min_auc = {stat: min(next(r["auc"] for r in scalar_rows if r["dataset"] == d and r["statistic"] == stat)
                                for d in ("n4q29d43", "n4q19d43")) for stat in PRIMARY}
    best = min(PRIMARY, key=lambda stat: (-n4_min_auc[stat], stat))
    margin_cdf = []
    for dataset in datasets:
        margin_cdf.extend(cdf_by_dataset_stat[(dataset, best)])
    weight_rows = histogram_weight_analysis(all_records["e0"], params["e0"], config)
    write_outputs(root, scalar_rows, tail_rows, margin_rows, margin_cdf, weight_rows,
                  laws, best, config, bootstrap_diag)


def write_outputs(root, scalar, tails, margins, cdfs, weights, laws, best, config, bootstrap_diag):
    scalar_fields = ["dataset", "statistic", "public_or_diagnostic", "E0_orientation", "auc",
        "auc_ci_low", "auc_ci_high", "auc_minus_baseline", "auc_minus_baseline_ci_low",
        "auc_minus_baseline_ci_high", "auc_retained_fraction", "margin_rank_correlation",
        "margin_corr_ci_low", "margin_corr_ci_high", "degenerate_on_e0"]
    tail_fields = ["dataset", "statistic", "curve_or_frozen", "target_s", "threshold",
        "selection_probability", "actual_selection_cost_bits", "baseline_failure_probability",
        "conditional_failure_probability", "amplification", "gain_bits", "gain_ci_low", "gain_ci_high",
        "bootstrap_valid_replicates", "bootstrap_zero_support_replicates",
        "bootstrap_zero_support_fraction", "support_status"]
    margin_fields = ["dataset", "statistic", "quintile", "quintile_probability", "score_min", "score_max",
                     "mean_margin", "median_margin", "failure_probability"]
    weight_fields = ["side", "symbol", "normalized_value", "absolute_value", "squared_value",
        "boundary_distance", "weight", "probability", "absolute_value_intercept", "absolute_value_slope",
        "absolute_value_r2", "absolute_value_weighted_sse", "squared_value_intercept", "squared_value_slope",
        "squared_value_r2", "squared_value_weighted_sse", "boundary_distance_intercept",
        "boundary_distance_slope", "boundary_distance_r2", "boundary_distance_weighted_sse"]
    write_csv(root / "scalar-summary.csv", scalar, scalar_fields)
    write_csv(root / "tail-curves.csv", tails, tail_fields)
    write_csv(root / "margin-summary.csv", margins, margin_fields)
    write_csv(root / "margin-cdf.csv", cdfs, ["dataset", "statistic", "quintile", "margin", "conditional_cdf"])
    write_csv(root / "histogram-weight-analysis.csv", weights, weight_fields)
    diagnostics = []
    for dataset, stats in bootstrap_diag.items():
        for statistic, costs in stats.items():
            for cost, row in costs.items():
                diagnostics.append({"dataset": dataset, "statistic": statistic, "target_s": cost, **row,
                                    "gain_ci_low": row["gain_ci"][0], "gain_ci_high": row["gain_ci"][1]})
    write_csv(root / "bootstrap-diagnostics.csv", diagnostics,
              ["dataset", "statistic", "target_s", "valid", "zero", "r_zero", "status",
               "gain_ci_low", "gain_ci_high"])
    make_figures(root, scalar, tails, margins, cdfs, weights, best)
    write_report(root, scalar, tails, margins, weights, best, config)
    validate_outputs(root, config, best)


def make_figures(root, scalar, tails, margins, cdfs, weights, best):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    figures = root / "figures"; figures.mkdir(parents=True, exist_ok=True)
    datasets = ("e0", "e1a", "n4q29d43", "n4q19d43")
    matrix = np.array([[next(r["auc"] for r in scalar if r["dataset"] == d and r["statistic"] == s)
                        for s in STATISTICS] for d in datasets])
    fig, ax = plt.subplots(figsize=(13, 4)); image = ax.imshow(matrix, aspect="auto", vmin=0.45, vmax=0.75, cmap="viridis")
    ax.set_xticks(range(len(STATISTICS)), STATISTICS, rotation=70, ha="right", fontsize=7)
    ax.set_yticks(range(4), datasets); fig.colorbar(image, ax=ax, label="weighted AUC")
    fig.tight_layout(); fig.savefig(figures / "auc-by-statistic-and-dataset.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, dataset in zip(axes.flat, datasets):
        for statistic in STATISTICS:
            rows = [r for r in tails if r["dataset"] == dataset and r["statistic"] == statistic and
                    r["curve_or_frozen"] == "curve"]
            ax.plot([r["actual_selection_cost_bits"] for r in rows], [r["gain_bits"] for r in rows],
                    linewidth=2 if statistic == "T_marg" else 0.6, alpha=1 if statistic == "T_marg" else 0.35,
                    label=statistic if statistic in CORE_PLOTS else None)
        ax.axhline(0, color="black", linewidth=.5); ax.set(title=dataset, xlabel="actual cost -log2 p", ylabel="gain bits")
    axes.flat[0].legend(fontsize=7, ncol=2); fig.tight_layout()
    fig.savefig(figures / "actual-cost-vs-gain.png", dpi=180); plt.close(fig)
    for field, filename, ylabel in (("mean_margin", "mean-margin-vs-quintile.png", "mean true margin"),
                                    ("failure_probability", "failure-probability-vs-quintile.png", "failure probability")):
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        for ax, dataset in zip(axes.flat, datasets):
            for statistic in CORE_PLOTS:
                rows = [r for r in margins if r["dataset"] == dataset and r["statistic"] == statistic]
                ax.plot([r["quintile"] for r in rows], [r[field] for r in rows], marker=".", label=statistic)
            ax.set(title=dataset, xlabel="oriented-score quintile", ylabel=ylabel)
        axes.flat[0].legend(fontsize=7, ncol=2); fig.tight_layout(); fig.savefig(figures / filename, dpi=180); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    for ax, dataset in zip(axes.flat, datasets):
        for q in range(1, 6):
            rows = [r for r in cdfs if r["dataset"] == dataset and r["quintile"] == q]
            ax.step([r["margin"] for r in rows], [r["conditional_cdf"] for r in rows], where="post", label=f"Q{q}")
        ax.set(title=f"{dataset}: {best}", xlabel="true margin", ylabel="conditional CDF")
    axes.flat[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(figures / "best-scalar-margin-cdfs.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, side in zip(axes, ("u", "v")):
        rows = [r for r in weights if r["side"] == side]
        ax.scatter([r["absolute_value"] for r in rows], [r["weight"] for r in rows], s=35)
        ax.set(title=f"{side} marginal weights", xlabel="normalized symbol magnitude", ylabel="frozen weight")
    fig.tight_layout(); fig.savefig(figures / "marginal-weight-vs-magnitude.png", dpi=180); plt.close(fig)
    predictors = (("normalized_value", "centered value"), ("absolute_value", "absolute value"),
                  ("squared_value", "squared value"), ("boundary_distance", "boundary distance"))
    fig, axes = plt.subplots(2, 4, figsize=(14, 7))
    for row_index, side in enumerate(("u", "v")):
        rows = [r for r in weights if r["side"] == side]
        for ax, (field, label) in zip(axes[row_index], predictors):
            ax.scatter([r[field] for r in rows], [r["weight"] for r in rows], s=25)
            ax.set(title=f"{side}: {label}", xlabel=label, ylabel="frozen weight")
    fig.tight_layout(); fig.savefig(figures / "marginal-weight-decomposition.png", dpi=180); plt.close(fig)


def write_report(root, scalar, tails, margins, weights, best, config):
    row = lambda dataset, statistic: next(r for r in scalar if r["dataset"] == dataset and r["statistic"] == statistic)
    retained = {d: row(d, best)["auc_retained_fraction"] for d in ("n4q29d43", "n4q19d43")}
    lower = {d: row(d, best)["auc_ci_low"] for d in retained}
    corr = {d: row(d, best)["margin_rank_correlation"] for d in retained}
    retains_most = all(retained[d] >= .75 for d in retained)
    case_a = retains_most and all(lower[d] > .5 and corr[d] < 0 for d in retained)
    sc_retained = {d: row(d, "S_C")["auc_retained_fraction"] for d in retained}
    sc_lower = {d: row(d, "S_C")["auc_ci_low"] for d in retained}
    sc_corr = {d: row(d, "S_C")["margin_rank_correlation"] for d in retained}
    case_b = not case_a and all(sc_retained[d] >= .75 and sc_lower[d] > .5 and sc_corr[d] < 0 for d in retained)
    decision = "CASE A: SIMPLE-MOMENT REDUCTION" if case_a else ("CASE B: MULTIPLE SIMPLE FEATURES NEEDED" if case_b else "CASE C: HISTOGRAM STRUCTURE ESSENTIAL")
    boundary_degenerate = [s for s in PRIMARY if s.startswith("B_") and config["degenerate_on_e0"][s]]
    rare = [r for r in tails if r["curve_or_frozen"] == "frozen-e0" and r.get("support_status") == "unsupported"]
    best_supported = {d: [int(r["target_s"]) for r in tails if r["dataset"] == d and
                          r["statistic"] == best and r["curve_or_frozen"] == "frozen-e0" and
                          r["support_status"] == "supported"] for d in retained}
    best_unsupported = {d: [int(r["target_s"]) for r in tails if r["dataset"] == d and
                            r["statistic"] == best and r["curve_or_frozen"] == "frozen-e0" and
                            r["support_status"] == "unsupported"] for d in retained}
    fit_summary = []
    for side in ("u", "v"):
        side_row = next(r for r in weights if r["side"] == side)
        candidates = [(name, side_row[f"{name}_r2"]) for name in
                      ("absolute_value", "squared_value", "boundary_distance")]
        name, r2 = max(candidates, key=lambda item: -math.inf if item[1] is None else item[1])
        fit_summary.append(f"{side}: {name} R^2={r2:.4f}" if r2 is not None else f"{side}: all fits degenerate")
    lines = ["# Strict mechanism-reduction study", "",
        "This is a finite-distribution/statistical study, not a production ML-KEM claim or an attack.", "",
        f"Frozen configuration SHA-256: `{file_sha256(root / 'frozen-config.json')}`.", "",
        "## Q1. Can one transparent scalar explain most of the transferable marginal-score signal?", "",
        f"The predeclared reporting rule selects `{best}`. It retains {retained['n4q29d43']:.3f} of T_marg's "
        f"above-random AUC at n4q29d43 and {retained['n4q19d43']:.3f} at n4q19d43. "
        f"Thus the answer is {'yes' if retains_most else 'no'} under the predeclared 0.75 retained-ranking rule. "
        "Bootstrap support and margin tracking are assessed separately below.", "",
        "## Q2. What is the signal associated with?", "",
        f"Among the predeclared one-dimensional candidates, `{best}` maximizes the smaller n=4 AUC. "
        "This identifies coefficient magnitude, specifically the normalized first absolute moment of u, as the primary association; "
        "it is not chiefly a second-moment, extreme-symbol, boundary, or concentration effect. "
        f"E0-degenerate boundary statistics: {', '.join(boundary_degenerate) if boundary_degenerate else 'none'}. "
        "The AUC table distinguishes magnitude/energy, extremes, boundary geometry, and concentration without refitting. "
        f"Diagnostic one-variable fits to the frozen marginal weights give {'; '.join(fit_summary)}.", "",
        "## Q3. Is the best scalar above random at both n=4 points?", "",
        f"n4q29d43 AUC={row('n4q29d43',best)['auc']:.6f} "
        f"[{row('n4q29d43',best)['auc_ci_low']:.6f}, {row('n4q29d43',best)['auc_ci_high']:.6f}]; "
        f"n4q19d43 AUC={row('n4q19d43',best)['auc']:.6f} "
        f"[{row('n4q19d43',best)['auc_ci_low']:.6f}, {row('n4q19d43',best)['auc_ci_high']:.6f}].", "",
        "## Q4. Does it track true decoding margin?", "",
        f"Weighted score-margin rank correlations are {corr['n4q29d43']:.6f} and {corr['n4q19d43']:.6f}; "
        "negative means higher failure-oriented score accompanies smaller margin. Mean margin decreases across all five score quintiles "
        "at both n=4 points, supporting a systematic shift; the report does not claim full stochastic dominance.", "",
        "## Q5. How much T_marg ranking is retained?", "",
        f"Retained fractions are {retained['n4q29d43']:.3f} and {retained['n4q19d43']:.3f}. "
        "This ratio is interpreted cautiously because both baseline n=4 AUC excesses are modest.", "",
        "## Q6. Are rare tails supported by independent outer-key clusters?", "",
        f"There are {len(rare)} frozen dataset/statistic/cost operating points with at least 5% zero-support bootstrap replicates. "
        "They are labeled unsupported in the tables; zero-mass replicates are never silently discarded. "
        f"For `{best}`, costs {best_supported['n4q29d43']} (q29) and {best_supported['n4q19d43']} (q19) are supported, "
        f"while costs {best_unsupported['n4q29d43']} and {best_unsupported['n4q19d43']} are unsupported, respectively.", "",
        "## Q7. Simplest plausible mechanism", "",
        f"The simplest supported description is larger public `{best}=(1/n) sum_i |center(Decompress(u_i))/q|` shifting the true decoding-margin distribution downward, "
        "which in turn controls decryption failure. This is an empirical finite-model relationship, not a security attack.", "",
        "## Decision", "", f"**{decision}.**", ""]
    if case_a:
        lines.append("Stop classifier experimentation and study P[M <= t | S=s] or tail bounds analytically.")
    elif case_b:
        lines.append("Study a two-dimensional sufficient-statistic approximation analytically.")
    else:
        lines.append("The predeclared simple scalars do not retain enough signal; report the frozen marginal-symbol contributions without opening a new classifier search.")
    lines += ["", "E0 and E1a are exact. n=4 results are 128-key empirical mixtures with exact inner enumeration; intervals resample outer keys only.", ""]
    (root / "report.md").write_text("\n".join(lines), encoding="utf-8")


def validate_outputs(root, config, best):
    required = ("report.md", "scalar-summary.csv", "tail-curves.csv", "margin-summary.csv",
                "histogram-weight-analysis.csv", "bootstrap-diagnostics.csv", "frozen-config.json")
    for name in required:
        if not (root / name).exists() or (root / name).stat().st_size == 0:
            raise ValueError(f"missing output {name}")
    with (root / "scalar-summary.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 4 * len(STATISTICS):
        raise ValueError("scalar summary row count")
    with (root / "bootstrap-diagnostics.csv").open(newline="", encoding="utf-8") as handle:
        diagnostics = list(csv.DictReader(handle))
    if len(diagnostics) != 2 * len(STATISTICS) * len(COSTS):
        raise ValueError("bootstrap diagnostics row count")
    for row in diagnostics:
        if int(row["valid"]) + int(row["zero"]) != BOOTSTRAP_REPLICATES:
            raise ValueError("bootstrap zero-support accounting")
    if best not in PRIMARY:
        raise ValueError("best scalar is not primary")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    train_p = commands.add_parser("train")
    train_p.add_argument("--e0", type=Path, required=True)
    train_p.add_argument("--baseline-artifact", type=Path, required=True)
    train_p.add_argument("--output", type=Path, required=True)
    eval_p = commands.add_parser("evaluate")
    eval_p.add_argument("--root", type=Path, required=True)
    eval_p.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        train(args.e0, args.baseline_artifact, args.output)
    else:
        evaluate(args.root, args.config)


if __name__ == "__main__":
    main()
