import csv
import gzip
import json
import math
import tempfile
import unittest
from pathlib import Path

import frozen_normalized_transfer as frozen


def histogram(*bins):
    values = [0] * 16
    for index in bins:
        values[index] += 1
    return tuple(values)


class FrozenNormalizedTransferTests(unittest.TestCase):
    def test_feature_parse_and_mass(self):
        value = "K=7|" + ".".join(["1", "1"] + ["0"] * 14) + "|M=-2"
        cluster, counts, margin = frozen.parse_feature(value)
        self.assertEqual((cluster, sum(counts), margin), (7, 2, -2))

    def test_gzip_law_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "law.csv"
            with gzip.open(path.with_suffix(".csv.gz"), "wt", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["feature_id", "feature_value", "Nz", "Ez"])
                writer.writerow(["x", ".".join(["1"] + ["0"] * 15) + "|M=1", 3, 0])
            records = frozen.read_records(path)
            self.assertEqual(frozen.totals(records), (3, 0, 1))

    def test_exact_probability_mass_and_learning(self):
        records = [
            frozen.Record(histogram(0, 0), -1, 2, 2),
            frozen.Record(histogram(15, 15), 3, 6, 0),
        ]
        self.assertEqual(frozen.totals(records), (8, 2, 2))
        weights, evidence = frozen.learn_weights(records, lambda h: h)
        self.assertEqual(sum(map(int, evidence["all_numerators"])), 16)
        self.assertEqual(sum(map(int, evidence["failure_numerators"])), 4)
        self.assertGreater(weights[0], 0)
        self.assertLess(weights[15], 0)

    def test_threshold_and_weighted_auc(self):
        law = {0.0: [10, 0], 1.0: [10, 10]}
        threshold, p = frozen.calibrate_threshold(law, 0.5)
        self.assertEqual(threshold, 1.0)
        self.assertEqual(p, 0.5)
        _, auc = frozen.weighted_roc(law)
        self.assertEqual(auc, 1.0)
        _, tied_auc = frozen.weighted_roc({0.0: [20, 10]})
        self.assertEqual(tied_auc, 0.5)

    def test_frozen_serialization_and_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "e0"
            root.mkdir()
            path = root / "normalized_uv_margin.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["feature_id", "feature_value", "Nz", "Ez"])
                writer.writerow(["normalized_uv_margin", ".".join(["1", "1"] + ["0"] * 14) + "|M=-1", 2, 2])
                writer.writerow(["normalized_uv_margin", ".".join(["0"] * 14 + ["1", "1"]) + "|M=2", 6, 0])
            first, second = root / "first.json", root / "second.json"
            frozen.train(root, first)
            frozen.train(root, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            frozen.load_model(first)
            model = json.loads(first.read_text())
            model["epsilon"]["hex"] = (2.0 ** -20).hex()
            first.write_text(json.dumps(model), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "epsilon"):
                frozen.load_model(first)

    def test_margin_cdf_properties(self):
        records = [
            frozen.Record(histogram(0, 0), -1, 2, 2),
            frozen.Record(histogram(15, 15), 3, 6, 0),
        ]
        weights = {"joint": [0.0.hex()] * 16, "u": [0.0.hex()] * 4, "v": [0.0.hex()] * 4}
        rows = frozen.margin_diagnostics("toy", records, weights)
        self.assertEqual(rows[-1]["conditional_cdf"], 1.0)
        self.assertTrue(all(0 <= row["conditional_cdf"] <= 1 for row in rows))


if __name__ == "__main__":
    unittest.main()
