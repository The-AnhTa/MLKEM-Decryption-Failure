import csv
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import analyze
import conditional_independence
import predicate_transfer
import sampled_key_ci
import summarize_matrix


class AnalysisTests(unittest.TestCase):
    def test_synthetic_modes_do_not_reuse_ciphertext_results(self):
        root = Path("results/e0")
        self.assertEqual(summarize_matrix.analysis_directory(root, "none", "ciphertext"),
                         root / "ciphertext-none")
        self.assertEqual(summarize_matrix.analysis_directory(root, "no-compression", "ciphertext"),
                         root / "ciphertext-no-compression")
        self.assertEqual(summarize_matrix.analysis_directory(root, "independent-compression", "ciphertext"),
                         root / "undefined-ciphertext-observable")
        self.assertEqual(summarize_matrix.analysis_directory(root, "none", "hist_v"),
                         root / "ciphertext-none")

    def test_metrics_and_universal_bound(self):
        rows = [("a", 80, 8), ("b", 20, 12)]
        total, failures, d2, dinf, frontier = analyze.metrics(rows)
        self.assertEqual((total, failures), (100, 20))
        self.assertGreater(d2, 0)
        self.assertAlmostEqual(dinf, math.log2(3))
        for _, p, amplification in frontier:
            self.assertLessEqual(amplification, 1 / p)
        budgets = analyze.budgeted_frontier(rows, max_bits=5)
        self.assertEqual([item["b"] for item in budgets], [1, 2, 3, 4, 5])
        for item in budgets:
            self.assertLessEqual(item["amplification_float"], 2 ** item["b"])
        self.assertAlmostEqual(budgets[0]["amplification_float"], 1.5)

    def test_independent_output_is_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            output = Path(temporary) / "output"
            source.mkdir()
            with (source / "pk.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["feature_id", "feature_value", "Nz", "Ez"])
                writer.writerow(["pk", "a", 3, 1])
                writer.writerow(["pk", "b", 7, 4])
            with (source / "coordinate_marginals.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["coordinate", "total", "correct", "failures"])
                writer.writerow([0, 10, 9, 1])
                writer.writerow([1, 10, 8, 2])
            analyze.independent_output(source, output)
            rows = analyze.load_law(output / "pk.csv")
            _, _, d2, dinf, _ = analyze.metrics(rows)
            self.assertAlmostEqual(d2, 0.0)
            self.assertAlmostEqual(dinf, 0.0)

    def test_streaming_summary_matches_in_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "law.csv"
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["feature_id", "feature_value", "Nz", "Ez"])
                writer.writerow(["x", "a", 80, 8])
                writer.writerow(["x", "b", 20, 12])
            rows = analyze.load_law(path)
            total, failures, d2, dinf, _ = analyze.metrics(rows)
            streamed = analyze.streaming_metrics(path)
            self.assertEqual(streamed[:2], (total, failures))
            self.assertAlmostEqual(streamed[2], d2)
            self.assertAlmostEqual(streamed[3], dinf)
            self.assertEqual(streamed[4], ("b", 20, 12))

    def test_conditionally_independent_derivation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pk_coordinate_marginals.csv"
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["feature_value", "coordinate", "Nz", "Eiz"])
                writer.writerow(["pk0", 0, 100, 10])
                writer.writerow(["pk0", 1, 100, 20])
                writer.writerow(["pk1", 0, 100, 0])
                writer.writerow(["pk1", 1, 100, 0])
            total, cells = conditional_independence.derive(path)
            self.assertEqual(total, 200)
            self.assertEqual(cells[0][2], Fraction(7, 25))
            analysis = conditional_independence.analyze_cells(total, cells, max_bits=4)
            self.assertEqual(len(analysis["budgets"]), 4)
            self.assertGreater(analysis["Dinf_bits"], 0)

    def test_sampled_key_confidence_interval(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "secret_key.csv"
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["feature_id", "feature_value", "Nz", "Ez"])
                writer.writerow(["secret_key", "k0", 10, 1])
                writer.writerow(["secret_key", "k1", 10, 3])
            result = sampled_key_ci.analyze(path)
            self.assertAlmostEqual(result["mean_exact_conditional_failure"], 0.2)
            self.assertLessEqual(result["lower"], 0.2)
            self.assertGreaterEqual(result["upper"], 0.2)

    def test_transfer_selector_is_frozen(self):
        cells = {"high": (20, 10), "low": (80, 0)}
        groups = {Fraction(5): 20, Fraction(0): 80}
        selector = predicate_transfer.selector_for_budget(groups, 100, 1)
        self.assertEqual(selector["threshold_score"], "0/1")
        self.assertEqual(selector["boundary_probability"], "3/8")
        scores = {"high": Fraction(5), "low": Fraction(0)}
        mass, failures = predicate_transfer.evaluate_selector(cells, scores, selector, True)
        self.assertEqual(mass, 50)
        self.assertEqual(failures, 10)
        target = {"high": (10, 4), "low": (90, 9), "unseen": (20, 10)}
        mass, failures = predicate_transfer.evaluate_selector(target, scores, selector, True)
        self.assertEqual(mass, Fraction(175, 4))
        self.assertEqual(failures, Fraction(59, 8))


if __name__ == "__main__":
    unittest.main()
