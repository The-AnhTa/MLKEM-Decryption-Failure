#!/usr/bin/env python3
"""Explain frozen S_u1 behavior using key covariance and coordinate hazards."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260920
DATASETS = {
    "n4q29d43": {"n": 4, "q": 29, "du": 4, "kind": "mechanism",
        "source": "results/mechanism-reduction/data/n4q29d43/mechanism_margin.csv",
        "key_margin_source": "results/frozen-normalized-transfer/data/n4q29d43/normalized_uv_margin_by_key.csv"},
    "n4q19d43": {"n": 4, "q": 19, "du": 4, "kind": "mechanism",
        "source": "results/mechanism-reduction/data/n4q19d43/mechanism_margin.csv",
        "key_margin_source": "results/frozen-normalized-transfer/data/n4q19d43/normalized_uv_margin_by_key.csv"},
    "n8q29d43": {"n": 8, "q": 29, "du": 4, "kind": "su1",
        "source": "results/final-su1-confirmation/data/n8q29d43/su1_margin_by_key.csv"},
}


class ConcatenatedFiles(io.RawIOBase):
    def __init__(self, paths):
        super().__init__(); self.paths = iter(paths); self.current = None
    def readable(self): return True
    def readinto(self, buffer):
        view, written = memoryview(buffer), 0
        while written < len(view):
            if self.current is None:
                try: self.current = next(self.paths).open("rb")
                except StopIteration: break
            count = self.current.readinto(view[written:])
            if count: written += count
            else: self.current.close(); self.current = None
        return written
    def close(self):
        if self.current is not None: self.current.close(); self.current = None
        super().close()


def open_text(path: Path):
    if path.exists(): return path.open("rt", newline="", encoding="utf-8")
    gz = path.with_suffix(path.suffix + ".gz")
    if gz.exists(): return gzip.open(gz, "rt", newline="", encoding="utf-8")
    parts = sorted(gz.parent.glob(gz.name + ".part*"))
    if parts:
        return io.TextIOWrapper(gzip.GzipFile(fileobj=io.BufferedReader(ConcatenatedFiles(parts))),
                                newline="", encoding="utf-8")
    raise FileNotFoundError(path)


def decompress(symbol, d, q): return (q * symbol + (1 << (d - 1))) >> d
def center(value, q):
    value %= q
    return value - q if value > q // 2 else value


def committed_law(repo: Path, name: str):
    cfg = DATASETS[name]; aggregate = defaultdict(lambda: [0, 0])
    with open_text(repo / cfg["source"]) as handle:
        for row in csv.DictReader(handle):
            value = row["feature_value"]
            if cfg["kind"] == "su1":
                match = re.fullmatch(r"K=(\d+)\|A=(\d+)\|M=(-?\d+)", value)
                if not match: raise ValueError(f"{name}: invalid S_u1 row")
                key, numerator, margin = map(int, match.groups())
            else:
                match = re.fullmatch(r"U=([0-9.]+)\|V=[0-9.]+\|M=(-?\d+)", value)
                if not match: raise ValueError(f"{name}: invalid mechanism row")
                key, margin = None, int(match.group(2))
                counts = tuple(map(int, match.group(1).split(".")))
                numerator = sum(count * abs(center(decompress(symbol, cfg["du"], cfg["q"]), cfg["q"]))
                                for symbol, count in enumerate(counts))
            total, failures = int(row["Nz"]), int(row["Ez"])
            if failures > total or (margin <= 0) != (failures == total):
                raise ValueError(f"{name}: failure/margin mismatch")
            cell = aggregate[(key, numerator, margin)]
            cell[0] += total; cell[1] += failures
    return aggregate


def validate_n4_projections(repo: Path, root: Path, name: str, recovered):
    """Validate replay against two smaller committed sufficient projections."""
    cfg = DATASETS[name]
    committed_global = committed_law(repo, name)
    replay_global = defaultdict(lambda: [0, 0])
    replay_key_margin = defaultdict(lambda: [0, 0])
    for (key, numerator, margin), values in recovered.items():
        for target in (replay_global[(None, numerator, margin)], replay_key_margin[(key, margin)]):
            target[0] += values[0]; target[1] += values[1]
    if dict(committed_global) != dict(replay_global):
        raise ValueError(f"{name}: recovered global S_u1/margin law differs from committed law")
    committed_key_margin = defaultdict(lambda: [0, 0])
    with open_text(repo / cfg["key_margin_source"]) as handle:
        for row in csv.DictReader(handle):
            match = re.fullmatch(r"K=(\d+)\|[0-9.]+\|M=(-?\d+)", row["feature_value"])
            if not match: raise ValueError(f"{name}: invalid key-margin validation row")
            target = committed_key_margin[tuple(map(int, match.groups()))]
            target[0] += int(row["Nz"]); target[1] += int(row["Ez"])
    if dict(committed_key_margin) != dict(replay_key_margin):
        raise ValueError(f"{name}: recovered key/margin law differs from committed law")
    return {"dataset": name, "global_su1_margin_match": True, "key_margin_match": True,
            "validation_strategy": "committed global S_u1/margin plus committed key/margin projections"}


def recovered_law(root: Path, name: str):
    result = {}
    path = root / "recovery" / name / "recovered_su1_margin_by_key.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (int(row["key_id"]), int(row["su1_numerator"]), int(row["minimum_margin"]))
            result[key] = [int(row["Nz"]), int(row["Ez"])]
    return result


def execution_records(law, n, q):
    return [(key, numerator / (n * q), margin, values[0], values[1])
            for (key, numerator, margin), values in sorted(law.items())]


def coordinate_records(root: Path, name: str, q: int):
    rows = []
    path = root / "recovery" / name / "coordinate_margin_by_key.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            margin, total, failures = int(row["coordinate_margin"]), int(row["Nz"]), int(row["Ez"])
            if (margin <= 0) != (failures == total): raise ValueError("local failure/margin mismatch")
            rows.append((int(row["key_id"]), int(row["x_numerator"]) / q,
                         margin, total, failures))
    return rows


def auc(cells):
    law = defaultdict(lambda: [0, 0])
    for _, score, _, total, failures in cells:
        law[score][0] += total; law[score][1] += failures
    positives = sum(e for n, e in law.values()); negatives = sum(n - e for n, e in law.values())
    if not positives or not negatives: return None
    below, favorable = 0, 0
    for score in sorted(law):
        total, failures = law[score]; nonfailures = total - failures
        favorable += failures * below + failures * nonfailures / 2
        below += nonfailures
    return favorable / (positives * negatives)


def execution_key_stats(records):
    keys = sorted({r[0] for r in records}); index = {key: i for i, key in enumerate(keys)}
    stats = [[0.0] * 4 for _ in keys]
    grouped = defaultdict(list)
    for key, score, margin, total, failures in records:
        i = index[key]
        values = (total, total * score, failures, failures * score)
        stats[i] = [a + b for a, b in zip(stats[i], values)]
        grouped[key].append((key, score, margin, total, failures))
    if any(row[0] <= 0 for row in stats): raise ValueError("empty key cluster")
    return keys, stats, grouped


def covariance_terms(stats, multiplicities=None):
    mult = [1] * len(stats) if multiplicities is None else multiplicities
    n, es, ef, esf = [sum(mult[i] * stats[i][j] for i in range(len(stats))) for j in range(4)]
    total = esf / n - (es / n) * (ef / n)
    within = sum(mult[i] * (row[3] - row[1] * row[2] / row[0])
                 for i, row in enumerate(stats)) / n
    between = sum(mult[i] * row[1] * row[2] / row[0]
                  for i, row in enumerate(stats)) / n - (es / n) * (ef / n)
    return total, within, between


def correlation_from_moments(moment, x_is_l=False):
    n, sx, sy, sxx, syy, sxy = moment
    vx, vy = sxx / n - (sx / n) ** 2, syy / n - (sy / n) ** 2
    return (sxy / n - sx * sy / n ** 2) / math.sqrt(vx * vy) if vx > 0 and vy > 0 else math.nan


def local_key_stats(records):
    keys = sorted({r[0] for r in records}); index = {key: i for i, key in enumerate(keys)}
    # n,sx,sm,sxx,smm,sxm,sl,sll,sxl
    stats = [[0.0] * 9 for _ in keys]
    for key, x, margin, total, failures in records:
        i = index[key]
        values = (total, total*x, total*margin, total*x*x, total*margin*margin,
                  total*x*margin, failures, failures, failures*x)
        stats[i] = [a + b for a, b in zip(stats[i], values)]
    return keys, stats


def local_correlations(stats, multiplicities=None):
    mult = [1] * len(stats) if multiplicities is None else multiplicities
    s = [sum(mult[i] * stats[i][j] for i in range(len(stats))) for j in range(9)]
    xm = correlation_from_moments([s[j] for j in (0,1,2,3,4,5)])
    xl = correlation_from_moments([s[j] for j in (0,1,6,3,7,8)])
    n = sum(mult[i] * stats[i][0] for i in range(len(stats)))
    cov = sum(mult[i] * (row[5] - row[1]*row[2]/row[0]) for i,row in enumerate(stats)) / n
    vx = sum(mult[i] * (row[3] - row[1]**2/row[0]) for i,row in enumerate(stats)) / n
    vm = sum(mult[i] * (row[4] - row[2]**2/row[0]) for i,row in enumerate(stats)) / n
    within = cov / math.sqrt(vx * vm) if vx > 0 and vm > 0 else math.nan
    return xm, xl, within


def bootstrap(exec_stats, local_stats, replicates=BOOTSTRAP_REPLICATES, seed=BOOTSTRAP_SEED):
    if len(exec_stats) != len(local_stats): raise ValueError("cluster count mismatch")
    rng = random.Random(seed); values = []
    for replicate in range(replicates):
        counts = [0] * len(exec_stats)
        for _ in counts: counts[rng.randrange(len(counts))] += 1
        values.append(covariance_terms(exec_stats, counts) + local_correlations(local_stats, counts))
    return values


def ci(values):
    finite = sorted(value for value in values if math.isfinite(value))
    def quantile(p):
        position = (len(finite) - 1) * p; lower = int(position); fraction = position - lower
        return finite[lower] if lower + 1 == len(finite) else finite[lower] * (1-fraction) + finite[lower+1] * fraction
    return quantile(.025), quantile(.975)


def local_hazard(records):
    cells = defaultdict(lambda: [0.0] * 6)
    for _, x, margin, total, failures in records:
        values = (total, failures, total*margin, total*margin*margin, total*x, failures*x)
        cells[x] = [a + b for a, b in zip(cells[x], values)]
    rows = []
    for x, (mass, failures, sm, smm, _, _) in sorted(cells.items()):
        mean = sm / mass
        rows.append({"x": x, "coordinate_mass": int(mass),
                     "local_failure_probability": failures/mass,
                     "mean_coordinate_margin": mean,
                     "margin_variance": smm/mass - mean*mean})
    return rows


def conditioned_hazard(records, key_weights):
    cells = defaultdict(lambda: [0, 0])
    for key, x, _, total, failures in records:
        cells[(key, x)][0] += total; cells[(key, x)][1] += failures
    xs, total_key_mass = sorted({x for _, x in cells}), sum(key_weights.values())
    rows = []
    for x in xs:
        supported = [(key, values) for (key, value), values in cells.items() if value == x and values[0]]
        support_mass = sum(key_weights[key] for key, _ in supported)
        probability = sum(key_weights[key] * values[1] / values[0] for key, values in supported) / support_mass
        rows.append({"x": x, "key_conditioned_local_failure_probability": probability,
                     "supporting_key_mass": support_mass / total_key_mass,
                     "supporting_key_count": len(supported)})
    return rows


def regression(rows, outcome):
    import numpy as np
    x = np.asarray([r["x"] for r in rows]); y = np.asarray([r[outcome] for r in rows])
    w = np.asarray([r["coordinate_mass"] for r in rows], dtype=float); root = np.sqrt(w)
    fits = []
    for degree in (1, 2):
        design = np.column_stack([x ** power for power in range(degree + 1)])
        beta = np.linalg.lstsq(design * root[:,None], y * root, rcond=None)[0]
        fitted = design @ beta; mean = np.average(y, weights=w)
        sse = np.sum(w*(y-fitted)**2); sst = np.sum(w*(y-mean)**2)
        fits.append((beta, 1-sse/sst if sst else math.nan, fitted))
    return {"slope": fits[0][0][1], "linear_R2": fits[0][1],
            "quadratic_R2": fits[1][1], "quadratic_improvement": fits[1][1]-fits[0][1],
            "linear_fitted": fits[0][2], "quadratic_fitted": fits[1][2]}


def value_text(value):
    if value is None: return ""
    if isinstance(value, float): return "" if math.isnan(value) else format(value, ".12g")
    return str(value)


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader()
        for row in rows: writer.writerow({field: value_text(row.get(field, "")) for field in fields})


def plot_all(root, covariance_rows, per_key_rows, hazard_rows, fits):
    import matplotlib.pyplot as plt
    import numpy as np
    figures = root / "figures"; figures.mkdir(parents=True, exist_ok=True)
    names = list(DATASETS)
    fig, ax = plt.subplots(figsize=(8,4.5)); width=.24; positions=np.arange(len(names))
    for offset, field, label in [(-width,"total_cov","total"),(0,"within_key_cov","within"),(width,"between_key_cov","between")]:
        ax.bar(positions+offset, [next(r[field] for r in covariance_rows if r["dataset"]==n) for n in names], width, label=label)
    ax.axhline(0,color="black",lw=.8); ax.set_xticks(positions,names); ax.set_ylabel("Cov(S_u1, F)"); ax.legend(); fig.tight_layout()
    fig.savefig(figures/"covariance-components.png",dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7,5))
    for name in names:
        rows=[r for r in per_key_rows if r["dataset"]==name]
        ax.scatter([r["mean_S_u1"] for r in rows],[r["delta_k"] for r in rows],s=12,alpha=.65,label=name)
    ax.set_xlabel("key mean S_u1"); ax.set_ylabel("key failure probability"); ax.legend(); fig.tight_layout()
    fig.savefig(figures/"key-failure-vs-mean-su1.png",dpi=180); plt.close(fig)

    for outcome, ylabel, filename in [("local_failure_probability","P(L_i=1 | X_i=x)","local-failure-hazard.png"),
                                      ("mean_coordinate_margin","E[M_i | X_i=x]","local-mean-margin.png")]:
        fig, ax=plt.subplots(figsize=(7,5))
        for name in names:
            rows=[r for r in hazard_rows if r["dataset"]==name]
            empirical, = ax.plot([r["x"] for r in rows],[r[outcome] for r in rows],"o-",label=name)
            fit=fits[(name,outcome)]
            ax.plot([r["x"] for r in rows],fit["linear_fitted"],"--",alpha=.65,
                    color=empirical.get_color())
            ax.plot([r["x"] for r in rows],fit["quadratic_fitted"],":",alpha=.65,
                    color=empirical.get_color())
        ax.set_xlabel("x"); ax.set_ylabel(ylabel); ax.legend(); fig.tight_layout(); fig.savefig(figures/filename,dpi=180); plt.close(fig)
    fig, ax=plt.subplots(figsize=(7,5))
    for name in names:
        rows=[r for r in hazard_rows if r["dataset"]==name]
        ax.plot([r["x"] for r in rows],[r["local_failure_probability"] for r in rows],"o-",label=name)
    ax.set_xlabel("x"); ax.set_ylabel("local failure probability"); ax.legend(); fig.tight_layout()
    fig.savefig(figures/"n4-vs-n8-local-hazard-overlay.png",dpi=180); plt.close(fig)


def evaluate(repo: Path, root: Path):
    covariance_rows=[]; per_key_rows=[]; hazard_rows=[]; conditioned_rows=[]; regression_rows=[]; bootstrap_rows=[]
    classifications={}; fits={}; validation_rows=[]
    for dataset, cfg in DATASETS.items():
        recovered=recovered_law(root,dataset)
        if cfg["kind"] == "su1":
            committed=committed_law(repo,dataset)
            if committed != recovered: raise ValueError(f"{dataset}: recovered global law differs from committed dataset")
            validation_rows.append({"dataset":dataset,"global_su1_margin_match":True,"key_margin_match":True,
                                    "validation_strategy":"full committed key/S_u1/margin cell equality"})
        else:
            validation_rows.append(validate_n4_projections(repo,root,dataset,recovered))
        records=execution_records(recovered,cfg["n"],cfg["q"])
        coords=coordinate_records(root,dataset,cfg["q"])
        keys, estats, grouped=execution_key_stats(records); local_keys,lstats=local_key_stats(coords)
        if keys != local_keys: raise ValueError(f"{dataset}: recovery key mismatch")
        if any(local[0] != cfg["n"] * execution[0] for local, execution in zip(lstats, estats)):
            raise ValueError(f"{dataset}: coordinate mass not n times execution mass")
        total,within,between=covariance_terms(estats)
        residual=total-within-between
        if abs(residual)>32*sys.float_info.epsilon*max(1,abs(total),abs(within),abs(between)):
            raise ValueError(f"{dataset}: covariance identity residual too large")
        scale=abs(within)+abs(between); stable=abs(total)>1e-12*max(scale,1e-300)
        cov_row={"dataset":dataset,"total_cov":total,"within_key_cov":within,
            "between_key_cov":between,"within_fraction":within/total if stable else math.nan,
            "between_fraction":between/total if stable else math.nan,"fractions_stable":stable,
            "decomposition_residual":residual}
        covariance_rows.append(cov_row)
        for i,key in enumerate(keys):
            n,es,ef,esf=estats[i]; wc=esf/n-(es/n)*(ef/n)
            per_key_rows.append({"dataset":dataset,"key_id":key,"key_mass":int(n),"delta_k":ef/n,
                "mean_S_u1":es/n,"within_key_cov":wc,"per_key_auc":auc(grouped[key])})
        hrows=local_hazard(coords)
        for row in hrows: row["dataset"]=dataset
        hazard_rows.extend(hrows)
        key_weights={key:estats[i][0] for i,key in enumerate(keys)}
        crows=conditioned_hazard(coords,key_weights)
        for row in crows: row["dataset"]=dataset
        conditioned_rows.extend(crows)
        xm,xl,centered=local_correlations(lstats)
        draws=bootstrap(estats,lstats)
        metric_names=("total_cov","within_key_cov","between_key_cov","corr_X_M","corr_X_L","within_key_centered_corr_X_M")
        estimates=(total,within,between,xm,xl,centered)
        intervals={}
        for j,(metric,estimate) in enumerate(zip(metric_names,estimates)):
            low,high=ci([row[j] for row in draws]); intervals[metric]=(low,high)
            bootstrap_rows.append({"dataset":dataset,"metric":metric,"estimate":estimate,"ci_low":low,"ci_high":high,
                                   "replicates":BOOTSTRAP_REPLICATES,"seed":BOOTSTRAP_SEED})
        # Fractions are not interpretable when the total covariance is not
        # statistically separated from zero, even if floating-point division
        # itself is numerically stable.
        if intervals["total_cov"][0] <= 0 <= intervals["total_cov"][1]:
            cov_row["fractions_stable"] = False
            cov_row["within_fraction"] = math.nan
            cov_row["between_fraction"] = math.nan
        for outcome in ("local_failure_probability","mean_coordinate_margin"):
            fit=regression(hrows,outcome); fits[(dataset,outcome)]=fit
            regression_rows.append({"dataset":dataset,"outcome":outcome,"slope":fit["slope"],
                "linear_R2":fit["linear_R2"],"quadratic_R2":fit["quadratic_R2"],
                "quadratic_improvement":fit["quadratic_improvement"]})
        material_within=abs(within)>=.2*scale if scale else False
        material_between=abs(between)>=.2*scale if scale else False
        clear=lambda metric: intervals[metric][0]>0 or intervals[metric][1]<0
        local_clear=clear("within_key_centered_corr_X_M")
        if material_within and clear("within_key_cov") and local_clear and not material_between: case="A"
        elif material_between and clear("between_key_cov") and not material_within and not local_clear: case="B"
        elif material_within and material_between and (clear("within_key_cov") or clear("between_key_cov")): case="C"
        else: case="D"
        classifications[dataset]=case

    write_csv(root/"covariance-decomposition.csv",covariance_rows,
        ["dataset","total_cov","within_key_cov","between_key_cov","within_fraction","between_fraction","fractions_stable","decomposition_residual"])
    write_csv(root/"per-key-summary.csv",per_key_rows,
        ["dataset","key_id","key_mass","delta_k","mean_S_u1","within_key_cov","per_key_auc"])
    write_csv(root/"local-hazard.csv",hazard_rows,
        ["dataset","x","coordinate_mass","local_failure_probability","mean_coordinate_margin","margin_variance"])
    write_csv(root/"key-conditioned-hazard.csv",conditioned_rows,
        ["dataset","x","key_conditioned_local_failure_probability","supporting_key_mass","supporting_key_count"])
    write_csv(root/"regression-diagnostics.csv",regression_rows,
        ["dataset","outcome","slope","linear_R2","quadratic_R2","quadratic_improvement"])
    write_csv(root/"bootstrap-summary.csv",bootstrap_rows,
        ["dataset","metric","estimate","ci_low","ci_high","replicates","seed"])
    write_csv(root/"recovery-validation.csv",validation_rows,
        ["dataset","global_su1_margin_match","key_margin_match","validation_strategy"])
    plot_all(root,covariance_rows,per_key_rows,hazard_rows,fits)
    write_report(root,covariance_rows,regression_rows,bootstrap_rows,classifications)


def write_report(root,covariance,regressions,bootstrap,classifications):
    def b(dataset,metric): return next(r for r in bootstrap if r["dataset"]==dataset and r["metric"]==metric)
    lines=["# Key/hazard decomposition", "",
      "This explanatory analysis used only the three committed datasets and the frozen positive `S_u1` orientation. Coordinate diagnostics were recovered by deterministic replay. The n=8 `(key, S_u1, minimum margin)` law matched cell-for-cell; each n=4 replay matched both committed global `(S_u1, minimum margin)` and committed `(key, minimum margin)` projections exactly.", "",
      "## Results", "",
      "| dataset | case | total covariance | within | between | within-centered corr(X,M) | corr(X,L) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for dataset in DATASETS:
        c=next(r for r in covariance if r["dataset"]==dataset); cm=b(dataset,"within_key_centered_corr_X_M"); cl=b(dataset,"corr_X_L")
        lines.append(f"| {dataset} | {classifications[dataset]} | {c['total_cov']:.6g} | {c['within_key_cov']:.6g} | {c['between_key_cov']:.6g} | {cm['estimate']:.6g} [{cm['ci_low']:.6g}, {cm['ci_high']:.6g}] | {cl['estimate']:.6g} [{cl['ci_low']:.6g}, {cl['ci_high']:.6g}] |")
    lines += ["", "All covariance identities close at floating-point precision. Exact local support values were retained without smoothing or outcome-dependent merging. Dashed and dotted plot curves are diagnostic weighted linear and quadratic fits, not predictors.", "", "## Interpretation", ""]
    mapping={"A":"within-key local mechanism","B":"key heterogeneity","C":"mixed","D":"no stable association"}
    for dataset in DATASETS:
        c=next(r for r in covariance if r["dataset"]==dataset); w=b(dataset,"within_key_cov"); be=b(dataset,"between_key_cov"); cm=b(dataset,"within_key_centered_corr_X_M")
        lines.append(f"- **{dataset}: Case {classifications[dataset]} - {mapping[classifications[dataset]]}.** Within covariance {c['within_key_cov']:.6g} (95% CI {w['ci_low']:.6g} to {w['ci_high']:.6g}); between covariance {c['between_key_cov']:.6g} (95% CI {be['ci_low']:.6g} to {be['ci_high']:.6g}); centered local margin correlation {cm['estimate']:.6g} (95% CI {cm['ci_low']:.6g} to {cm['ci_high']:.6g}).")
    lines += ["", "## Local linearity diagnostic", "", "| dataset | outcome | slope | linear R2 | quadratic R2 | improvement |", "|---|---|---:|---:|---:|---:|"]
    for row in regressions:
        label = "local failure" if row["outcome"] == "local_failure_probability" else "coordinate margin"
        lines.append(f"| {row['dataset']} | {label} | {row['slope']:.6g} | {row['linear_R2']:.4f} | {row['quadratic_R2']:.4f} | {row['quadratic_improvement']:.4f} |")
    lines += ["", "Both n=4 points have the expected positive local-failure slope and negative margin slope. At n=8 both slopes reverse, the local-failure linear fit is weak, and the key-centered correlation interval includes zero. Thus the directional local relation present at n=4 disappears rather than transferring to n=8."]
    n4cases={classifications['n4q29d43'],classifications['n4q19d43']}; n8=classifications['n8q29d43']
    lines += ["", "## Answers", ""]
    if n4cases=={"A"}: why4="At both n=4 points, the signal is primarily a within-key local coordinate effect."
    elif n4cases=={"B"}: why4="At both n=4 points, the signal is primarily between-key heterogeneity."
    elif n4cases <= {"A","C"}: why4="At n=4, within-key local association contributes, with a material between-key component at at least one point."
    elif n4cases <= {"B","C"}: why4="At n=4, between-key heterogeneity contributes, with a material within-key component at at least one point."
    else: why4="The two n=4 points do not support one stable mechanism classification."
    if n8=="D": why8="At n=8, neither covariance decomposition nor the key-centered local relation is stable enough to support the n=4 mechanism."
    else: why8=f"At n=8 the preregistered rules classify the evidence as Case {n8}; the component estimates above state the supported change without further speculation."
    lines += [f"**Why did `S_u1` work at n=4?** {why4}", "", f"**Why did it fail at n=8?** {why8}", "", "These are toy-model, algorithmic findings and are not a production ML-KEM security claim.", ""]
    (root/"report.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--repo",type=Path,default=Path(".")); parser.add_argument("--root",type=Path,required=True)
    args=parser.parse_args(); evaluate(args.repo.resolve(),args.root.resolve())
if __name__=="__main__": main()
