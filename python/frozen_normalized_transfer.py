#!/usr/bin/env python3
"""Train on E0 and evaluate the frozen normalized ciphertext scores."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


EPSILON = 2.0 ** -40
COSTS = (2, 4, 6, 8, 10)
BIN_EDGES = ("-1/2", "-1/4", "0", "1/4", "1/2")
BOOTSTRAP_SEED = 20260914
BOOTSTRAP_REPLICATES = 10_000
SCORES = ("joint", "marginal")


@dataclass(frozen=True)
class Record:
    histogram: tuple[int, ...]
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
    raise FileNotFoundError(path)


def parse_feature(value: str) -> tuple[int | None, tuple[int, ...], int]:
    cluster = None
    if value.startswith("K="):
        prefix, value = value.split("|", 1)
        cluster = int(prefix[2:])
    histogram_text, margin_text = value.rsplit("|M=", 1)
    histogram = tuple(int(item) for item in histogram_text.split("."))
    if len(histogram) != 16 or any(item < 0 for item in histogram):
        raise ValueError("invalid normalized joint histogram")
    return cluster, histogram, int(margin_text)


def read_records(path: Path) -> list[Record]:
    records = []
    with open_text(path) as handle:
        for row in csv.DictReader(handle):
            cluster, histogram, margin = parse_feature(row["feature_value"])
            total, failures = int(row["Nz"]), int(row["Ez"])
            if failures > total or (margin <= 0) != (failures == total):
                raise ValueError(f"margin/failure inconsistency in {path}")
            records.append(Record(histogram, margin, total, failures, cluster))
    if not records:
        raise ValueError(f"empty law: {path}")
    return records


def totals(records: list[Record]) -> tuple[int, int, int]:
    n_values = {sum(record.histogram) for record in records}
    if len(n_values) != 1 or next(iter(n_values)) <= 0:
        raise ValueError("histogram mass is not a common positive n")
    return sum(r.total for r in records), sum(r.failures for r in records), next(iter(n_values))


def marginal_counts(histogram: tuple[int, ...], axis: str) -> tuple[int, ...]:
    if axis == "u":
        return tuple(sum(histogram[4 * u + v] for v in range(4)) for u in range(4))
    if axis == "v":
        return tuple(sum(histogram[4 * u + v] for u in range(4)) for v in range(4))
    raise ValueError(axis)


def learn_weights(records: list[Record], selector) -> tuple[list[float], dict]:
    total, failures, n = totals(records)
    width = len(selector(records[0].histogram))
    all_numerators = [0] * width
    fail_numerators = [0] * width
    for record in records:
        values = selector(record.histogram)
        for index, count in enumerate(values):
            all_numerators[index] += count * record.total
            fail_numerators[index] += count * record.failures
    if failures == 0:
        raise ValueError("E0 has no failures")
    probabilities = [value / (total * n) for value in all_numerators]
    fail_probabilities = [value / (failures * n) for value in fail_numerators]
    weights = [math.log((pf + EPSILON) / (p + EPSILON))
               for p, pf in zip(probabilities, fail_probabilities)]
    evidence = {
        "all_numerators": [str(x) for x in all_numerators],
        "all_denominator": str(total * n),
        "failure_numerators": [str(x) for x in fail_numerators],
        "failure_denominator": str(failures * n),
        "probabilities": probabilities,
        "failure_probabilities": fail_probabilities,
    }
    return weights, evidence


def score_histogram(histogram: tuple[int, ...], weights: dict, score_name: str) -> float:
    n = sum(histogram)
    if score_name == "joint":
        return math.fsum(float.fromhex(w) * count / n
                         for w, count in zip(weights["joint"], histogram))
    u = marginal_counts(histogram, "u")
    v = marginal_counts(histogram, "v")
    return math.fsum(float.fromhex(w) * count / n for w, count in zip(weights["u"], u)) + \
        math.fsum(float.fromhex(w) * count / n for w, count in zip(weights["v"], v))


def score_law(records: list[Record], weights: dict, score_name: str):
    law = defaultdict(lambda: [0, 0])
    for record in records:
        score = score_histogram(record.histogram, weights, score_name)
        law[score][0] += record.total
        law[score][1] += record.failures
    return dict(law)


def calibrate_threshold(law, target: float) -> tuple[float, float]:
    total = sum(cell[0] for cell in law.values())
    tail = 0
    candidates = []
    for threshold in sorted(law, reverse=True):
        tail += law[threshold][0]
        probability = tail / total
        candidates.append((abs(probability - target), -threshold, threshold, probability))
    _, _, threshold, probability = min(candidates)
    return threshold, probability


def metric_at(law, threshold: float) -> dict:
    total = sum(cell[0] for cell in law.values())
    failures = sum(cell[1] for cell in law.values())
    selected_total = sum(cell[0] for score, cell in law.items() if score >= threshold)
    selected_failures = sum(cell[1] for score, cell in law.items() if score >= threshold)
    delta = failures / total
    if selected_total == 0:
        return {"p": 0.0, "delta": delta, "conditional": None,
                "amplification": None, "gain": None}
    conditional = selected_failures / selected_total
    amplification = conditional / delta
    gain = math.log2(amplification) if amplification > 0 else -math.inf
    return {"p": selected_total / total, "delta": delta, "conditional": conditional,
            "amplification": amplification, "gain": gain}


def weighted_roc(law):
    positives = sum(cell[1] for cell in law.values())
    negatives = sum(cell[0] - cell[1] for cell in law.values())
    if positives == 0 or negatives == 0:
        return [], None
    favorable_twice = 0
    negatives_below = 0
    for score in sorted(law):
        total, positive = law[score]
        negative = total - positive
        favorable_twice += 2 * positive * negatives_below + positive * negative
        negatives_below += negative
    auc = favorable_twice / (2 * positives * negatives)
    points = [(0.0, 0.0, math.inf)]
    tp = fp = 0
    for score in sorted(law, reverse=True):
        total, positive = law[score]
        tp += positive
        fp += total - positive
        points.append((fp / negatives, tp / positives, score))
    return points, auc


def weight_object(values: list[float]) -> dict:
    return {"decimal": values, "hex": [value.hex() for value in values]}


def train(e0_path: Path, output: Path) -> dict:
    if "e0" not in {part.lower() for part in e0_path.parts}:
        raise ValueError("training input must be an explicitly named E0 directory")
    records = read_records(e0_path / "normalized_uv_margin.csv")
    joint, joint_evidence = learn_weights(records, lambda h: h)
    u, u_evidence = learn_weights(records, lambda h: marginal_counts(h, "u"))
    v, v_evidence = learn_weights(records, lambda h: marginal_counts(h, "v"))
    hex_weights = {"joint": [w.hex() for w in joint], "u": [w.hex() for w in u],
                   "v": [w.hex() for w in v]}
    thresholds = {}
    for score_name in SCORES:
        law = score_law(records, hex_weights, score_name)
        thresholds[score_name] = {}
        for cost in COSTS:
            threshold, probability = calibrate_threshold(law, 2.0 ** -cost)
            thresholds[score_name][str(cost)] = {
                "decimal": threshold, "hex": threshold.hex(),
                "selection_probability": probability,
            }
    source = e0_path / "normalized_uv_margin.csv"
    model = {
        "schema_version": 1,
        "training_dataset": "e0",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "bin_edges": list(BIN_EDGES),
        "bin_order": "row-major-u-then-v",
        "epsilon": {"expression": "2^-40", "hex": EPSILON.hex()},
        "logarithm": "natural",
        "selection_costs": list(COSTS),
        "threshold_rule": "closest absolute inclusive-tail probability; ties choose larger threshold",
        "weights": {"joint": weight_object(joint), "u": weight_object(u), "v": weight_object(v)},
        "evidence": {"joint": joint_evidence, "u": u_evidence, "v": v_evidence},
        "e0_thresholds": thresholds,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return model


def load_model(path: Path) -> tuple[dict, dict]:
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != 1 or model.get("training_dataset") != "e0":
        raise ValueError("not a frozen E0 score artifact")
    if tuple(model.get("bin_edges", ())) != BIN_EDGES:
        raise ValueError("frozen bin edges changed")
    if model.get("epsilon", {}).get("hex") != EPSILON.hex():
        raise ValueError("frozen epsilon changed")
    if tuple(model.get("selection_costs", ())) != COSTS or model.get("logarithm") != "natural":
        raise ValueError("frozen scoring convention changed")
    weights = {}
    for name, size in (("joint", 16), ("u", 4), ("v", 4)):
        entry = model.get("weights", {}).get(name, {})
        if len(entry.get("hex", ())) != size or len(entry.get("decimal", ())) != size:
            raise ValueError(f"invalid frozen {name} weights")
        decoded = [float.fromhex(value) for value in entry["hex"]]
        if any(a != b for a, b in zip(decoded, entry["decimal"])):
            raise ValueError(f"decimal/hex mismatch in frozen {name} weights")
        weights[name] = entry["hex"]
    for name in SCORES:
        if set(model.get("e0_thresholds", {}).get(name, {})) != {str(x) for x in COSTS}:
            raise ValueError("missing frozen thresholds")
        for entry in model["e0_thresholds"][name].values():
            if float.fromhex(entry["hex"]) != entry["decimal"]:
                raise ValueError("decimal/hex mismatch in frozen threshold")
    return model, weights


def metadata_params(directory: Path) -> dict:
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    match = re.fullmatch(r"n(\d+)-k(\d+)-q(\d+)-e\d+_\d+-d(\d+)_(\d+)", metadata["parameters"])
    if not match:
        raise ValueError("unrecognized parameter identifier")
    n, k, q, du, dv = map(int, match.groups())
    if k != 1:
        raise ValueError("normalized transfer study is predeclared for k=1")
    return {"n": n, "q": q, "du": du, "dv": dv, "metadata": metadata}


def value_text(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    if value == math.inf:
        return "inf"
    if value == -math.inf:
        return "-inf"
    return f"{value:.17g}" if isinstance(value, float) else str(value)


def percentile_interval(values):
    clean = sorted(value for value in values if not math.isnan(value))
    if not clean:
        return None, None
    return clean[math.floor(0.025 * (len(clean) - 1))], clean[math.ceil(0.975 * (len(clean) - 1))]


def bootstrap(records: list[Record], weights: dict, model: dict):
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("NumPy is required for the predeclared cluster bootstrap") from error
    clusters = sorted({r.cluster for r in records})
    if not clusters or clusters[0] is None:
        raise ValueError("cluster bootstrap requires explicit key indices")
    cluster_index = {cluster: i for i, cluster in enumerate(clusters)}
    prepared = {}
    for score_name in SCORES:
        scores = sorted({score_histogram(r.histogram, weights, score_name) for r in records})
        score_index = {score: i for i, score in enumerate(scores)}
        nt = np.zeros((len(clusters), len(scores)), dtype=np.float64)
        et = np.zeros_like(nt)
        for record in records:
            i = cluster_index[record.cluster]
            j = score_index[score_histogram(record.histogram, weights, score_name)]
            nt[i, j] += record.total
            et[i, j] += record.failures
        prepared[score_name] = (np.asarray(scores), nt, et)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.multinomial(len(clusters), [1 / len(clusters)] * len(clusters),
                            size=BOOTSTRAP_REPLICATES).astype(np.float64)
    output = {name: {"recalibrated": {cost: [] for cost in COSTS},
                     "frozen": {cost: [] for cost in COSTS}, "auc": []} for name in SCORES}
    delta = {"recalibrated": {cost: [] for cost in COSTS},
             "frozen": {cost: [] for cost in COSTS}}
    batch_size = 200
    for start in range(0, BOOTSTRAP_REPLICATES, batch_size):
        sample = draws[start:start + batch_size]
        batch_gains = {}
        for score_name in SCORES:
            scores, nt, et = prepared[score_name]
            nmat, emat = sample @ nt, sample @ et
            n_total = nmat.sum(axis=1)
            e_total = emat.sum(axis=1)
            baseline = e_total / n_total
            tail_n = np.cumsum(nmat[:, ::-1], axis=1)[:, ::-1]
            tail_e = np.cumsum(emat[:, ::-1], axis=1)[:, ::-1]
            batch_gains[score_name] = {"recalibrated": {}, "frozen": {}}
            with np.errstate(divide="ignore", invalid="ignore"):
                negative = nmat - emat
                below = np.cumsum(negative, axis=1) - negative
                favorable = (emat * (below + 0.5 * negative)).sum(axis=1)
                auc = favorable / (e_total * (n_total - e_total))
            output[score_name]["auc"].extend(auc.tolist())
            for cost in COSTS:
                diff = np.abs(tail_n / n_total[:, None] - 2.0 ** -cost)
                index = len(scores) - 1 - np.argmin(diff[:, ::-1], axis=1)
                rows = np.arange(len(index))
                with np.errstate(divide="ignore", invalid="ignore"):
                    gain = np.log2((tail_e[rows, index] / tail_n[rows, index]) / baseline)
                values = gain.tolist()
                output[score_name]["recalibrated"][cost].extend(values)
                batch_gains[score_name]["recalibrated"][cost] = values
                threshold = float.fromhex(model["e0_thresholds"][score_name][str(cost)]["hex"])
                fixed_index = int(np.searchsorted(scores, threshold, side="left"))
                if fixed_index == len(scores):
                    fixed = np.full(len(n_total), np.nan)
                else:
                    with np.errstate(divide="ignore", invalid="ignore"):
                        fixed = np.log2((tail_e[:, fixed_index] / tail_n[:, fixed_index]) / baseline)
                values = fixed.tolist()
                output[score_name]["frozen"][cost].extend(values)
                batch_gains[score_name]["frozen"][cost] = values
        for mode in ("recalibrated", "frozen"):
            for cost in COSTS:
                delta[mode][cost].extend(
                    (a - b for a, b in zip(batch_gains["joint"][mode][cost],
                                           batch_gains["marginal"][mode][cost])))
    intervals = {name: {"recalibrated": {}, "frozen": {},
                        "auc": percentile_interval(output[name]["auc"])} for name in SCORES}
    for name in SCORES:
        for mode in ("recalibrated", "frozen"):
            for cost in COSTS:
                intervals[name][mode][cost] = percentile_interval(output[name][mode][cost])
    intervals["delta"] = {mode: {cost: percentile_interval(delta[mode][cost]) for cost in COSTS}
                          for mode in ("recalibrated", "frozen")}
    return intervals


def margin_diagnostics(dataset: str, records: list[Record], weights: dict):
    grouped = defaultdict(lambda: defaultdict(int))
    score_mass = defaultdict(int)
    for record in records:
        score = score_histogram(record.histogram, weights, "joint")
        score_mass[score] += record.total
        grouped[score][record.margin] += record.total
    total = sum(score_mass.values())
    assignments = {}
    cumulative = 0
    for score in sorted(score_mass):
        mass = score_mass[score]
        quantile = min(4, int(5 * (cumulative + mass / 2) / total))
        assignments[score] = quantile
        cumulative += mass
    q_margin = [defaultdict(int) for _ in range(5)]
    q_scores = [[] for _ in range(5)]
    for score, margins in grouped.items():
        q = assignments[score]
        q_scores[q].append(score)
        for margin, mass in margins.items():
            q_margin[q][margin] += mass
    rows = []
    for q in range(5):
        mass = sum(q_margin[q].values())
        if not mass:
            continue
        mean = sum(margin * value for margin, value in q_margin[q].items()) / mass
        failures = sum(value for margin, value in q_margin[q].items() if margin <= 0) / mass
        cumulative = 0
        for margin in sorted(q_margin[q]):
            cumulative += q_margin[q][margin]
            rows.append({"dataset": dataset, "quantile": q + 1,
                         "quantile_probability": mass / total,
                         "score_min": min(q_scores[q]), "score_max": max(q_scores[q]),
                         "margin": margin, "conditional_cdf": cumulative / mass,
                         "mean_margin": mean, "failure_probability": failures})
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: value_text(row.get(field)) for field in fields})


def make_figures(output: Path, transfer_rows, comparison_rows, margin_rows, roc_data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for mode, filename in (("recalibrated", "G-vs-selection-cost.png"),
                           ("frozen", "frozen-threshold-transfer.png")):
        fig, ax = plt.subplots(figsize=(8, 5))
        for dataset in sorted({r["dataset"] for r in transfer_rows}):
            for score in SCORES:
                rows = sorted((r for r in transfer_rows if r["dataset"] == dataset and
                               r["score"] == score and r["evaluation_mode"] == mode),
                              key=lambda r: r["target_s"])
                values = [r["gain_bits"] for r in rows]
                ax.plot([r["target_s"] for r in rows], values, marker="o",
                        linestyle="-" if score == "joint" else "--", label=f"{dataset} {score}")
        ax.axhline(0, color="black", linewidth=0.7)
        ax.set(xlabel="selection cost s", ylabel="gain G (bits)")
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout(); fig.savefig(figures / filename, dpi=180); plt.close(fig)

    datasets = sorted(roc_data)
    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    for ax, dataset in zip(axes.flat, datasets):
        for score in SCORES:
            points, auc = roc_data[dataset][score]
            ax.plot([p[0] for p in points], [p[1] for p in points], label=f"{score}, AUC={auc:.3f}")
        ax.plot([0, 1], [0, 1], color="gray", linestyle=":")
        ax.set(title=dataset, xlabel="false-positive rate", ylabel="true-positive rate")
        ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figures / "joint-vs-marginal.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    for ax, dataset in zip(axes.flat, datasets):
        for quantile in range(1, 6):
            rows = [r for r in margin_rows if r["dataset"] == dataset and r["quantile"] == quantile]
            ax.step([r["margin"] for r in rows], [r["conditional_cdf"] for r in rows],
                    where="post", label=f"Q{quantile}")
        ax.set(title=dataset, xlabel="true decoding margin M", ylabel="conditional CDF")
        ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(figures / "margin-CDF-by-score-quantile.png", dpi=180); plt.close(fig)


def evaluate(root: Path, artifact: Path):
    model, weights = load_model(artifact)
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    datasets = {
        "e0": root / "data" / "e0",
        "e1a": root / "data" / "e1a",
        "n4q29d43": root / "data" / "n4q29d43",
        "n4q19d43": root / "data" / "n4q19d43",
    }
    transfer_rows, comparison_rows, margin_rows = [], [], []
    roc_data, bootstrap_intervals = {}, {}
    laws = {}
    for dataset, directory in datasets.items():
        params = metadata_params(directory)
        filename = "normalized_uv_margin_by_key.csv" if dataset.startswith("n4") else "normalized_uv_margin.csv"
        records = read_records(directory / filename)
        source_total, source_failures, source_n = totals(records)
        global_meta = params["metadata"]["laws"]["global"]
        if source_total != int(global_meta["N"]) or source_failures != int(global_meta["E"]):
            raise ValueError(f"{dataset}: sufficient-statistic law does not preserve global mass")
        if source_n != params["n"]:
            raise ValueError(f"{dataset}: histogram mass does not equal n")
        if dataset.startswith("n4"):
            cluster_mass = defaultdict(int)
            for record in records:
                cluster_mass[record.cluster] += record.total
            if set(cluster_mass) != set(range(128)) or len(set(cluster_mass.values())) != 1:
                raise ValueError(f"{dataset}: sampled-key clusters are incomplete or unequal")
        laws[dataset] = {}
        if dataset.startswith("n4"):
            bootstrap_intervals[dataset] = bootstrap(records, weights, model)
        roc_data[dataset] = {}
        for score_name in SCORES:
            law = score_law(records, weights, score_name)
            laws[dataset][score_name] = law
            roc_data[dataset][score_name] = weighted_roc(law)
            for mode in ("recalibrated", "frozen"):
                for cost in COSTS:
                    if mode == "recalibrated":
                        threshold, _ = calibrate_threshold(law, 2.0 ** -cost)
                    else:
                        threshold = float.fromhex(model["e0_thresholds"][score_name][str(cost)]["hex"])
                    metric = metric_at(law, threshold)
                    if dataset.startswith("n4"):
                        ci = bootstrap_intervals[dataset][score_name][mode][cost]
                    else:
                        ci = (metric["gain"], metric["gain"])
                    transfer_rows.append({"dataset": dataset, **{k: params[k] for k in ("n", "q", "du", "dv")},
                        "score": score_name, "evaluation_mode": mode, "target_s": cost,
                        "threshold": threshold, "selection_probability": metric["p"],
                        "baseline_failure_probability": metric["delta"],
                        "conditional_failure_probability": metric["conditional"],
                        "amplification": metric["amplification"], "gain_bits": metric["gain"],
                        "ci_low": ci[0], "ci_high": ci[1], "frozen_score_sha256": artifact_digest})
        for mode in ("recalibrated", "frozen"):
            for cost in COSTS:
                jr = next(r for r in transfer_rows if r["dataset"] == dataset and r["score"] == "joint" and
                          r["evaluation_mode"] == mode and r["target_s"] == cost)
                mr = next(r for r in transfer_rows if r["dataset"] == dataset and r["score"] == "marginal" and
                          r["evaluation_mode"] == mode and r["target_s"] == cost)
                delta_g = None if jr["gain_bits"] is None or mr["gain_bits"] is None else jr["gain_bits"] - mr["gain_bits"]
                delta_ci = bootstrap_intervals[dataset]["delta"][mode][cost] if dataset.startswith("n4") else (delta_g, delta_g)
                comparison_rows.append({"dataset": dataset, "evaluation_mode": mode, "target_s": cost,
                    "joint_gain_bits": jr["gain_bits"], "marginal_gain_bits": mr["gain_bits"],
                    "delta_gain_bits": delta_g, "delta_ci_low": delta_ci[0], "delta_ci_high": delta_ci[1],
                    "joint_auc": roc_data[dataset]["joint"][1], "marginal_auc": roc_data[dataset]["marginal"][1],
                    "joint_auc_ci_low": (bootstrap_intervals[dataset]["joint"]["auc"][0] if dataset.startswith("n4") else roc_data[dataset]["joint"][1]),
                    "joint_auc_ci_high": (bootstrap_intervals[dataset]["joint"]["auc"][1] if dataset.startswith("n4") else roc_data[dataset]["joint"][1]),
                    "marginal_auc_ci_low": (bootstrap_intervals[dataset]["marginal"]["auc"][0] if dataset.startswith("n4") else roc_data[dataset]["marginal"][1]),
                    "marginal_auc_ci_high": (bootstrap_intervals[dataset]["marginal"]["auc"][1] if dataset.startswith("n4") else roc_data[dataset]["marginal"][1])})
        margin_rows.extend(margin_diagnostics(dataset, records, weights))

    transfer_fields = ["dataset", "n", "q", "du", "dv", "score", "evaluation_mode", "target_s",
        "threshold", "selection_probability", "baseline_failure_probability",
        "conditional_failure_probability", "amplification", "gain_bits", "ci_low", "ci_high",
        "frozen_score_sha256"]
    comparison_fields = ["dataset", "evaluation_mode", "target_s", "joint_gain_bits", "marginal_gain_bits",
        "delta_gain_bits", "delta_ci_low", "delta_ci_high", "joint_auc", "marginal_auc",
        "joint_auc_ci_low", "joint_auc_ci_high", "marginal_auc_ci_low", "marginal_auc_ci_high"]
    margin_fields = ["dataset", "quantile", "quantile_probability", "score_min", "score_max", "margin",
                     "conditional_cdf", "mean_margin", "failure_probability"]
    write_csv(root / "transfer-summary.csv", transfer_rows, transfer_fields)
    write_csv(root / "joint-vs-marginal.csv", comparison_rows, comparison_fields)
    write_csv(root / "margin-diagnostics.csv", margin_rows, margin_fields)
    roc_rows = []
    for dataset, score_data in roc_data.items():
        for score_name, (points, auc) in score_data.items():
            for fpr, tpr, threshold in points:
                roc_rows.append({"dataset": dataset, "score": score_name, "threshold": threshold,
                                 "false_positive_rate": fpr, "true_positive_rate": tpr, "auc": auc})
    write_csv(root / "roc-curves.csv", roc_rows,
              ["dataset", "score", "threshold", "false_positive_rate", "true_positive_rate", "auc"])
    make_figures(root, transfer_rows, comparison_rows, margin_rows, roc_data)
    write_report(root, transfer_rows, comparison_rows, margin_rows, artifact_digest)
    validate_outputs(root, artifact_digest)


def validate_outputs(root: Path, artifact_digest: str):
    with (root / "transfer-summary.csv").open(newline="", encoding="utf-8") as handle:
        transfer = list(csv.DictReader(handle))
    if len(transfer) != 4 * 2 * 2 * len(COSTS):
        raise ValueError("transfer summary has the wrong number of rows")
    if {row["frozen_score_sha256"] for row in transfer} != {artifact_digest}:
        raise ValueError("transfer summary artifact hash mismatch")
    for row in transfer:
        p = float(row["selection_probability"])
        if not 0 <= p <= 1:
            raise ValueError("invalid selection probability")
        if row["evaluation_mode"] == "frozen":
            model = json.loads((root / "frozen-score.json").read_text(encoding="utf-8"))
            expected = float.fromhex(model["e0_thresholds"][row["score"]][row["target_s"]]["hex"])
            if float(row["threshold"]) != expected:
                raise ValueError("frozen threshold changed during evaluation")
    with (root / "margin-diagnostics.csv").open(newline="", encoding="utf-8") as handle:
        margin = list(csv.DictReader(handle))
    grouped = defaultdict(list)
    for row in margin:
        grouped[(row["dataset"], row["quantile"])].append(row)
    for key, rows in grouped.items():
        rows.sort(key=lambda row: int(row["margin"]))
        cdf = [float(row["conditional_cdf"]) for row in rows]
        if any(a > b for a, b in zip(cdf, cdf[1:])) or not math.isclose(cdf[-1], 1.0):
            raise ValueError(f"non-CDF margin output for {key}")
    for filename in ("G-vs-selection-cost.png", "frozen-threshold-transfer.png",
                     "joint-vs-marginal.png", "margin-CDF-by-score-quantile.png"):
        if (root / "figures" / filename).stat().st_size == 0:
            raise ValueError(f"empty figure: {filename}")


def write_report(root: Path, transfer, comparison, margins, digest: str):
    def selected(dataset, score="joint", mode="recalibrated"):
        return [r for r in transfer if r["dataset"] == dataset and r["score"] == score and
                r["evaluation_mode"] == mode]
    lines = ["# Frozen normalized ciphertext-score transfer", "",
        "This is a finite-distribution/statistical-dependence experiment in the toy ML-KEM model. "
        "It is not evidence of a production ML-KEM vulnerability.", "",
        f"Frozen E0 artifact SHA-256: `{digest}`.", "",
        "## A. Does one frozen normalized score retain positive amplification from n=2 to n=4?", "",
        "**Answer: yes at the point-estimate level, but the effect is much weaker than at E0.** "
        "For q=19 every predeclared n=4 interval excludes zero; for q=29 only s=2 and s=4 do, "
        "while the rarer-selection intervals include zero.", ""]
    for dataset in ("e0", "e1a", "n4q29d43", "n4q19d43"):
        rows = selected(dataset)
        gains = ", ".join(f"s={r['target_s']}: {value_text(r['gain_bits'])}" for r in rows)
        lines.append(f"- **{dataset}:** joint-score gain bits {gains}.")
    lines += ["", "A positive gain means the unchanged E0 score retains failure amplification; n=4 "
              "intervals reflect only sampled-key uncertainty.", "",
              "## B. Does amplification remain when the numerical threshold is frozen?", "",
              "**Answer: partially, and not robustly at the rarest thresholds.** q=19 has positive "
              "point estimates at every E0 threshold, but only s=2 and s=4 exclude zero. q=29 is "
              "positive through s=6 at the point-estimate level and becomes strongly negative at "
              "s=8 and s=10. E1a has nonzero selected mass only at s=2.", ""]
    for dataset in ("e1a", "n4q29d43", "n4q19d43"):
        rows = selected(dataset, mode="frozen")
        values = ", ".join(f"s={r['target_s']}: p={value_text(r['selection_probability'])}, "
                           f"G={value_text(r['gain_bits'])}" for r in rows)
        lines.append(f"- **{dataset}:** {values}.")
    lines += ["", "Thresholds above are copied bit-for-bit from E0. `NA` means the numerical "
              "predicate selected no evaluation mass.", "",
              "## C. Is the joint u-v score materially stronger than the marginal score?", "",
              "**Answer: not after transfer to n=4.** The two n=4 AUCs slightly favor the marginal "
              "score, and every n=4 delta-G interval includes zero. Joint structure is stronger in "
              "the rare E0 tail, but that advantage does not transfer consistently.", ""]
    for dataset in ("e0", "e1a", "n4q29d43", "n4q19d43"):
        rows = [r for r in comparison if r["dataset"] == dataset and r["evaluation_mode"] == "recalibrated"]
        deltas = ", ".join(f"s={r['target_s']}: {value_text(r['delta_gain_bits'])}" for r in rows)
        lines.append(f"- **{dataset}:** AUC joint={rows[0]['joint_auc']:.6g}, "
                     f"marginal={rows[0]['marginal_auc']:.6g}; delta-G {deltas}.")
    lines += ["", "Positive delta-G favors aligned joint u-v structure at that operating point; "
              "the AUC comparison summarizes all thresholds.", "",
              "## D. Does high public score shift executions toward the decoding boundary?", "",
              "**Answer: yes systematically in both n=4 mixtures, but not monotonically in E1a.** "
              "From the lowest to highest score quintile, mean margin falls and failure probability "
              "rises for both n=4 points. E0 has the same overall trend; E1a has substantial "
              "non-monotonicity across its middle quintiles.", ""]
    for dataset in ("e0", "e1a", "n4q29d43", "n4q19d43"):
        summaries = {}
        for row in margins:
            if row["dataset"] == dataset:
                summaries[row["quantile"]] = (row["mean_margin"], row["failure_probability"])
        text = ", ".join(f"Q{q}: E[M]={value_text(v[0])}, P[F]={value_text(v[1])}"
                         for q, v in sorted(summaries.items()))
        lines.append(f"- **{dataset}:** {text}.")
    lines += ["", "The conditional-CDF figure shows whether this change is a distribution-wide "
              "leftward shift rather than only a change in the failure tail.", "", "## Uncertainty and scope", "",
              "E0 and E1a probabilities are exact. Each n=4 point is the empirical mixture of 128 "
              "sampled outer keys with exact inner encapsulation enumeration. Its 95% intervals use "
              "the predeclared paired cluster bootstrap and are not population D-infinity bounds.", ""]
    lines += ["The optional n=8 extension was not run: the repository's predeclared E5 n=8 point "
              "has a certificate of empty failure support, and choosing a new nonzero-failure n=8 "
              "point after viewing these results would violate the frozen-transfer protocol.", ""]
    (root / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("--e0", type=Path, required=True)
    train_parser.add_argument("--output", type=Path, required=True)
    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("--root", type=Path, required=True)
    eval_parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        train(args.e0, args.output)
    else:
        evaluate(args.root, args.artifact)


if __name__ == "__main__":
    main()
