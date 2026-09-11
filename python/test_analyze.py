import csv
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import analyze
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

    def test_metrics_and_universal_bound(self):
        rows = [("a", 80, 8), ("b", 20, 12)]
        total, failures, d2, dinf, frontier = analyze.metrics(rows)
        self.assertEqual((total, failures), (100, 20))
        self.assertGreater(d2, 0)
        self.assertAlmostEqual(dinf, math.log2(3))
        for _, p, amplification in frontier:
            self.assertLessEqual(amplification, 1 / p)

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


if __name__ == "__main__":
    unittest.main()
