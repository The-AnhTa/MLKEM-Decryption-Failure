#!/usr/bin/env python3
"""Preregister and evaluate the final single-statistic S_u1 confirmation."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import frozen_normalized_transfer as frozen


CANDIDATES = ("n8q29d43", "n8q23d43", "n8q19d43")
PARAMETERS = {
    "n8q29d43": (8, 1, 29, 1, 1, 4, 3),
    "n8q23d43": (8, 1, 23, 1, 1, 4, 3),
    "n8q19d43": (8, 1, 19, 1, 1, 4, 3),
}
KEY_COUNT = 128
Y_PER_KEY = 4
DATA_SEED = 20260916
BOOTSTRAP_SEED = 20260918
BOOTSTRAP_REPLICATES = 10_000
FEASIBILITY_CAP = 4_000_000
ZERO_SUPPORT_LIMIT = 0.10
FROZEN_ORIENTATION = 1
HASHED_SOURCES = (
    "python/final_su1_confirmation.py",
    "docs/final-su1-confirmation-protocol.md",
    "src/enumerate.cpp", "src/features.cpp", "src/main.cpp", "src/params.cpp",
    "include/toy_mlkem/enumerate.hpp", "include/toy_mlkem/features.hpp",
)


@dataclass(frozen=True)
class Record:
    key: int
    numerator: int
    margin: int
    total: int
    failures: int


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value_text(value):
    return frozen.value_text(value)


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: value_text(row.get(field)) for field in fields})


def support_path(root: Path, candidate: str) -> Path:
    return root / "support" / candidate / "support_bound.json"


def selection_payload(root: Path, repo: Path) -> dict:
    points = []
    for candidate in CANDIDATES:
        certificate = json.loads(support_path(root, candidate).read_text(encoding="utf-8"))
        n, k, q, eta1, eta2, du, dv = PARAMETERS[candidate]
        expected = f"n{n}-k{k}-q{q}-e{eta1}_{eta2}-d{du}_{dv}"
        if certificate["parameters"] != expected:
            raise ValueError(f"{candidate}: support certificate parameter mismatch")
        work = KEY_COUNT * Y_PER_KEY * (3 ** n)
        feasible = work <= FEASIBILITY_CAP
        support_possible = not certificate["failure_impossible"]
        points.append({"preset": candidate, "parameters": {
            "n": n, "k": k, "q": q, "eta1": eta1, "eta2": eta2, "du": du, "dv": dv},
            "conditional_e1_work": work, "feasible": feasible,
            "support_possible": support_possible, "support_certificate": certificate,
            "support_certificate_sha256": sha256(support_path(root, candidate))})
    selected = next((point for point in points if point["feasible"] and point["support_possible"]), None)
    return {
        "schema_version": 1,
        "protocol": "docs/final-su1-confirmation-protocol.md",
        "study": "final-independent-frozen-Su1-confirmation",
        "candidate_order": list(CANDIDATES), "points": points,
        "selection_rule": "first ordered point with conditional_e1_work <= 4000000 and failure_impossible=false",
        "zero_failure_rule": "stop without fallback if selected experiment observes E=0",
        "selected_preset": selected["preset"] if selected else None,
        "selected_parameters": selected["parameters"] if selected else None,
        "sampling": {"key_count": KEY_COUNT, "y_per_key": Y_PER_KEY, "seed": DATA_SEED,
                     "exact_conditional_randomness": ["e1", "e2", "message"],
                     "bootstrap_cluster": "outer key"},
        "statistic": {"name": "S_u1", "orientation": FROZEN_ORIENTATION,
                      "formula": "sum_i abs(center(Decompress_du(u_i))) / (n*q)"},
        "analysis": {"auc_null": "AUC <= 0.5", "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                     "bootstrap_seed": BOOTSTRAP_SEED, "ci": "two-sided percentile 95%",
                     "tail_zero_support_rule": "UNSUPPORTED iff r_zero > 0.10",
                     "success": "auc_ci_low > 0.5 and margin_corr_ci_high < 0"},
        "feasibility_cap": FEASIBILITY_CAP,
        "source_sha256": {name: sha256(repo / name) for name in HASHED_SOURCES},
    }


def write_preregistration(root: Path, repo: Path) -> dict:
    payload = selection_payload(root, repo)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path = root / "preregistration.json"
    write_immutable(path, encoded)
    return payload


def write_immutable(path: Path, encoded: str):
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise ValueError("preregistration is immutable and differs from frozen rules/code")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(encoded, encoding="utf-8")


def verify_preregistration(root: Path, repo: Path) -> dict:
    path = root / "preregistration.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload != selection_payload(root, repo):
        raise ValueError("preregistration or frozen source hashes changed")
    return payload


def parse_feature(value: str):
    match = re.fullmatch(r"K=(\d+)\|A=(\d+)\|M=(-?\d+)", value)
    if not match:
        raise ValueError("invalid frozen S_u1 feature")
    return tuple(map(int, match.groups()))


def read_records(path: Path, n: int, q: int) -> list[Record]:
    records, key_n, key_e = [], [0] * KEY_COUNT, [0] * KEY_COUNT
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key, numerator, margin = parse_feature(row["feature_value"])
            total, failures = int(row["Nz"]), int(row["Ez"])
            if not 0 <= key < KEY_COUNT or not 0 <= numerator <= n * (q // 2):
                raise ValueError("key or S_u1 numerator outside frozen support")
            if failures > total or (margin <= 0) != (failures == total):
                raise ValueError("margin/failure mismatch")
            records.append(Record(key, numerator, margin, total, failures))
            key_n[key] += total; key_e[key] += failures
    if not records or len(set(key_n)) != 1 or key_n[0] == 0:
        raise ValueError("key clusters do not have equal positive exact conditional mass")
    return records


def score(record: Record, n: int, q: int) -> float:
    return FROZEN_ORIENTATION * record.numerator / (n * q)


def make_tensor(records, n, q):
    import numpy as np
    scores = np.asarray(sorted({score(record, n, q) for record in records}), dtype=np.float64)
    margins = np.asarray(sorted({record.margin for record in records}), dtype=np.int64)
    score_index = {value: i for i, value in enumerate(scores)}
    margin_index = {int(value): i for i, value in enumerate(margins)}
    tensor = np.zeros((KEY_COUNT, len(scores), len(margins)), dtype=np.float64)
    for record in records:
        tensor[record.key, score_index[score(record, n, q)], margin_index[record.margin]] += record.total
    return scores, margins, tensor


def law_from_joint(scores, margins, joint):
    failure_mask = margins <= 0
    return {float(score): [int(row.sum()), int(row[failure_mask].sum())]
            for score, row in zip(scores, joint) if row.sum()}


def weighted_rank_correlation(scores, margins, joint):
    score_mass, margin_mass = joint.sum(axis=1), joint.sum(axis=0)
    total = float(score_mass.sum())
    sr = (score_mass.cumsum() - score_mass + 0.5 * score_mass) / total
    mr = (margin_mass.cumsum() - margin_mass + 0.5 * margin_mass) / total
    ms, mm = float((score_mass * sr).sum() / total), float((margin_mass * mr).sum() / total)
    covariance = float((joint * sr[:, None] * mr[None, :]).sum() / total - ms * mm)
    vs = float((score_mass * sr * sr).sum() / total - ms * ms)
    vm = float((margin_mass * mr * mr).sum() / total - mm * mm)
    return covariance / math.sqrt(vs * vm) if vs and vm else None


def quintiles(scores, margins, joint):
    score_mass, total = joint.sum(axis=1), float(joint.sum())
    assignment, cumulative = [], 0.0
    for mass in score_mass:
        assignment.append(min(4, int(5 * (cumulative + float(mass) / 2) / total)))
        cumulative += float(mass)
    rows = []
    for quintile in range(5):
        indices = [i for i, value in enumerate(assignment) if value == quintile]
        if not indices:
            continue
        distribution = joint[indices].sum(axis=0)
        mass = float(distribution.sum())
        rows.append({"quintile": quintile + 1, "probability_mass": mass / total,
                     "score_min": float(scores[min(indices)]), "score_max": float(scores[max(indices)]),
                     "mean_margin": float((margins * distribution).sum() / mass),
                     "failure_probability": float(distribution[margins <= 0].sum() / mass)})
    if not math.isclose(sum(row["probability_mass"] for row in rows), 1.0):
        raise ValueError("quintile probability mass not conserved")
    return rows


def exact_tails(scores, margins, joint):
    score_mass = joint.sum(axis=1)
    failures = joint[:, margins <= 0].sum(axis=1)
    total, failure_total = float(score_mass.sum()), float(failures.sum())
    tail_n = score_mass[::-1].cumsum()[::-1]
    tail_e = failures[::-1].cumsum()[::-1]
    rows = []
    for index, threshold in enumerate(scores):
        probability = float(tail_n[index] / total)
        conditional = float(tail_e[index] / tail_n[index])
        amplification = conditional / (failure_total / total)
        rows.append({"threshold": float(threshold), "selection_probability": probability,
                     "actual_selection_cost_bits": actual_selection_cost(probability),
                     "baseline_failure_probability": failure_total / total,
                     "conditional_failure_probability": conditional,
                     "amplification": amplification,
                     "gain_bits": math.log2(amplification) if amplification > 0 else -math.inf})
    return rows


def actual_selection_cost(probability):
    if not 0 < probability <= 1:
        raise ValueError("selection probability must be in (0,1]")
    return -math.log2(probability)


def cluster_draws(count=KEY_COUNT, replicates=BOOTSTRAP_REPLICATES, seed=BOOTSTRAP_SEED):
    rng = random.Random(seed)
    output = []
    for _ in range(replicates):
        row = [0] * count
        for _ in range(count):
            row[rng.randrange(count)] += 1
        output.append(row)
    return output


def support_status(zero, replicates=BOOTSTRAP_REPLICATES):
    fraction = zero / replicates
    return fraction, "UNSUPPORTED" if fraction > ZERO_SUPPORT_LIMIT else "SUPPORTED"


def bootstrap(scores, margins, tensor):
    import numpy as np
    draws = np.asarray(cluster_draws(), dtype=np.float64)
    failure_mask = margins <= 0
    auc_values, correlation_values = [], []
    gain_values = [[] for _ in scores]
    zeros = [0] * len(scores)
    for start in range(0, BOOTSTRAP_REPLICATES, 200):
        weights = np.einsum("bc,csm->bsm", draws[start:start + 200], tensor, optimize=True)
        score_mass, margin_mass = weights.sum(axis=2), weights.sum(axis=1)
        total = score_mass.sum(axis=1)
        positives = weights[:, :, failure_mask].sum(axis=2)
        failure_total = positives.sum(axis=1)
        negatives = score_mass - positives
        below = np.cumsum(negatives, axis=1) - negatives
        with np.errstate(divide="ignore", invalid="ignore"):
            auc_values.extend(((positives * (below + 0.5 * negatives)).sum(axis=1) /
                               (failure_total * (total - failure_total))).tolist())
        sr = (np.cumsum(score_mass, axis=1) - score_mass + 0.5 * score_mass) / total[:, None]
        mr = (np.cumsum(margin_mass, axis=1) - margin_mass + 0.5 * margin_mass) / total[:, None]
        ms, mm = (score_mass * sr).sum(axis=1) / total, (margin_mass * mr).sum(axis=1) / total
        cross = (weights * sr[:, :, None] * mr[:, None, :]).sum(axis=(1, 2)) / total
        vs = (score_mass * sr * sr).sum(axis=1) / total - ms * ms
        vm = (margin_mass * mr * mr).sum(axis=1) / total - mm * mm
        with np.errstate(divide="ignore", invalid="ignore"):
            correlation_values.extend(((cross - ms * mm) / np.sqrt(vs * vm)).tolist())
        tail_n = np.cumsum(score_mass[:, ::-1], axis=1)[:, ::-1]
        tail_e = np.cumsum(positives[:, ::-1], axis=1)[:, ::-1]
        for index in range(len(scores)):
            zero = tail_n[:, index] == 0
            zeros[index] += int(zero.sum())
            valid = ~zero
            with np.errstate(divide="ignore", invalid="ignore"):
                gains = np.log2((tail_e[valid, index] / tail_n[valid, index]) /
                                (failure_total[valid] / total[valid]))
            gain_values[index].extend(gains.tolist())
    return {"auc_ci": frozen.percentile_interval(auc_values),
            "correlation_ci": frozen.percentile_interval(correlation_values),
            "gain_ci": [frozen.percentile_interval(values) for values in gain_values],
            "zeros": zeros}


def make_figures(root, auc, auc_ci, quintile_rows, tail_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figures = root / "figures"; figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.errorbar([0], [auc], yerr=[[auc - auc_ci[0]], [auc_ci[1] - auc]], fmt="o", capsize=5)
    ax.axhline(.5, color="black", linewidth=.8); ax.set(xlim=(-.5, .5), xticks=[0], xticklabels=["S_u1"], ylabel="weighted AUC")
    fig.tight_layout(); fig.savefig(figures / "auc-confirmation.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    q = [row["quintile"] for row in quintile_rows]
    axes[0].plot(q, [row["mean_margin"] for row in quintile_rows], marker="o")
    axes[0].set(xlabel="S_u1 quintile", ylabel="mean decoding margin")
    axes[1].plot(q, [row["failure_probability"] for row in quintile_rows], marker="o")
    axes[1].set(xlabel="S_u1 quintile", ylabel="failure probability")
    fig.tight_layout(); fig.savefig(figures / "quintile-diagnostics.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([row["actual_selection_cost_bits"] for row in tail_rows],
            [row["gain_bits"] for row in tail_rows], marker=".")
    ax.axhline(0, color="black", linewidth=.8); ax.set(xlabel="actual cost -log2 P[S_u1 >= tau]", ylabel="gain bits")
    fig.tight_layout(); fig.savefig(figures / "actual-cost-vs-gain.png", dpi=180); plt.close(fig)


def zero_failure_outputs(root, preset, total):
    write_csv(root / "summary.csv", [{"preset": preset, "N": total, "E": 0,
              "failure_probability": 0, "auc": None, "auc_ci_low": None, "auc_ci_high": None,
              "margin_rank_correlation": None, "margin_corr_ci_low": None,
              "margin_corr_ci_high": None, "confirmation_success": False}],
              ["preset", "N", "E", "failure_probability", "auc", "auc_ci_low", "auc_ci_high",
               "margin_rank_correlation", "margin_corr_ci_low", "margin_corr_ci_high", "confirmation_success"])
    for name, fields in (("quintiles.csv", ["quintile"]), ("tail-curves.csv", ["threshold"]),
                         ("bootstrap-diagnostics.csv", ["threshold"])):
        write_csv(root / name, [], fields)
    (root / "figures").mkdir(exist_ok=True)
    (root / "report.md").write_text(
        "# Final frozen-Su1 confirmation\n\n1. The preregistered point was evaluated and had zero observed failures.\n\n"
        "2. AUC greater than 0.5 cannot be evaluated.\n\n3. Significant negative margin association is not established.\n\n"
        "4. No tail-amplification claim is supported.\n\n5. The frozen S_u1 hypothesis is not confirmed by this zero-failure experiment.\n\n"
        "This finite toy-model result makes no production-ML-KEM security claim.\n", encoding="utf-8")


def evaluate(root: Path, repo: Path):
    prereg = verify_preregistration(root, repo)
    preset = prereg["selected_preset"]
    if preset is None:
        raise ValueError("no preregistered feasible support-positive point")
    data = root / "data" / preset
    metadata = json.loads((data / "metadata.json").read_text(encoding="utf-8"))
    params = prereg["selected_parameters"]
    expected_id = f"n{params['n']}-k{params['k']}-q{params['q']}-e{params['eta1']}_{params['eta2']}-d{params['du']}_{params['dv']}"
    expected_run = {"conditional_enumeration": "exact-e1-e2-message-given-key-y",
                    "enumeration": "sampled-keys-and-y", "key_count": str(KEY_COUNT),
                    "observable_scope": "frozen-su1-confirmation", "seed": str(DATA_SEED),
                    "y_per_key": str(Y_PER_KEY)}
    if metadata["parameters"] != expected_id or metadata["run"] != expected_run:
        raise ValueError("confirmation data do not match preregistration")
    records = read_records(data / "su1_margin_by_key.csv", params["n"], params["q"])
    total, failures = sum(r.total for r in records), sum(r.failures for r in records)
    meta = metadata["laws"]["global"]
    if total != int(meta["N"]) or failures != int(meta["E"]):
        raise ValueError("global probability mass not conserved")
    if failures == 0:
        zero_failure_outputs(root, preset, total)
        return
    scores, margins, tensor = make_tensor(records, params["n"], params["q"])
    joint = tensor.sum(axis=0)
    law = law_from_joint(scores, margins, joint)
    auc = frozen.weighted_roc(law)[1]
    correlation = weighted_rank_correlation(scores, margins, joint)
    quintile_rows = quintiles(scores, margins, joint)
    tail_rows = exact_tails(scores, margins, joint)
    boot = bootstrap(scores, margins, tensor)
    for index, row in enumerate(tail_rows):
        fraction, status = support_status(boot["zeros"][index])
        row.update({"gain_ci_low": boot["gain_ci"][index][0], "gain_ci_high": boot["gain_ci"][index][1],
                    "bootstrap_valid_replicates": BOOTSTRAP_REPLICATES - boot["zeros"][index],
                    "bootstrap_zero_support_replicates": boot["zeros"][index],
                    "bootstrap_zero_support_fraction": fraction, "support_status": status})
    auc_ci, corr_ci = boot["auc_ci"], boot["correlation_ci"]
    success = auc_ci[0] > .5 and corr_ci[1] < 0
    summary = [{"preset": preset, "N": total, "E": failures, "failure_probability": failures / total,
                "auc": auc, "auc_ci_low": auc_ci[0], "auc_ci_high": auc_ci[1],
                "margin_rank_correlation": correlation, "margin_corr_ci_low": corr_ci[0],
                "margin_corr_ci_high": corr_ci[1], "confirmation_success": success,
                "preregistration_sha256": sha256(root / "preregistration.json")}]
    write_csv(root / "summary.csv", summary, list(summary[0]))
    write_csv(root / "quintiles.csv", quintile_rows,
              ["quintile", "probability_mass", "score_min", "score_max", "mean_margin", "failure_probability"])
    tail_fields = ["threshold", "selection_probability", "actual_selection_cost_bits",
        "baseline_failure_probability", "conditional_failure_probability", "amplification", "gain_bits",
        "gain_ci_low", "gain_ci_high", "bootstrap_valid_replicates",
        "bootstrap_zero_support_replicates", "bootstrap_zero_support_fraction", "support_status"]
    write_csv(root / "tail-curves.csv", tail_rows, tail_fields)
    write_csv(root / "bootstrap-diagnostics.csv", tail_rows,
              ["threshold", "bootstrap_valid_replicates", "bootstrap_zero_support_replicates",
               "bootstrap_zero_support_fraction", "support_status", "gain_ci_low", "gain_ci_high"])
    make_figures(root, auc, auc_ci, quintile_rows, tail_rows)
    positive_supported = [row for row in tail_rows if row["support_status"] == "SUPPORTED" and
                          row["gain_ci_low"] is not None and row["gain_ci_low"] > 0]
    report = ["# Final frozen-Su1 confirmation", "",
        f"1. The preregistered point `{preset}` was successfully evaluated as a 128-key empirical mixture with four sampled y states per key and exact conditional enumeration of e1, e2, and messages.", "",
        f"2. {'Yes' if auc_ci[0] > .5 else 'No'}. Weighted AUC is {auc:.6f} with 95% key-cluster bootstrap CI [{auc_ci[0]:.6f}, {auc_ci[1]:.6f}].", "",
        f"3. {'Yes' if corr_ci[1] < 0 else 'No'}. Weighted score-margin rank correlation is {correlation:.6f} with 95% CI [{corr_ci[0]:.6f}, {corr_ci[1]:.6f}].", "",
        f"4. {len(positive_supported)} attainable tails have supported strictly positive 95% gain intervals. Unsupported rare tails are labeled in the tables and are not emphasized.", "",
        f"5. The frozen S_u1 mechanism hypothesis is {'CONFIRMED' if success else 'NOT CONFIRMED'} under the preregistered joint success rule.", "",
        "This is a finite toy-model confirmation study and makes no production-ML-KEM security claim.", ""]
    (root / "report.md").write_text("\n".join(report), encoding="utf-8")
    if len(quintile_rows) == 0 or len(tail_rows) != len(scores):
        raise ValueError("output structural validation failed")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prereg = commands.add_parser("preregister")
    prereg.add_argument("--root", type=Path, required=True)
    prereg.add_argument("--repo", type=Path, default=Path("."))
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--root", type=Path, required=True)
    evaluation.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "preregister":
        payload = write_preregistration(args.root, args.repo.resolve())
        print(payload["selected_preset"])
    else:
        evaluate(args.root, args.repo.resolve())


if __name__ == "__main__":
    main()
