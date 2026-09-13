import gzip
import math
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import mechanism_reduction as mechanism


class MechanismReductionTests(unittest.TestCase):
    def test_centered_decompression_and_exact_scalars(self):
        self.assertEqual(mechanism.decompress(7, 3, 17), 15)
        self.assertEqual(mechanism.center(15, 17), -2)
        values = mechanism.side_values((1, 0, 0, 0, 0, 0, 0, 1), 3, 17)
        self.assertEqual(values["m1"], Fraction(1, 17))
        self.assertEqual(values["m2"], Fraction(2, 17 * 17))
        self.assertEqual(values["concentration"], Fraction(1, 2))

    def test_boundary_definition(self):
        distance = mechanism.boundary_distance(0, 3, 17)
        self.assertEqual(distance, Fraction(1, 2))
        self.assertGreaterEqual(distance, 0)

    def test_auc_orientation_and_actual_cost(self):
        law = {0.0: [10, 10], 1.0: [10, 0]}
        _, auc = mechanism.frozen.weighted_roc(law)
        self.assertEqual(auc, 0.0)
        self.assertEqual(mechanism.orientation_from_auc(auc), -1)
        rows = mechanism.tail_curve({0.0: [12, 2], 1.0: [4, 2]})
        self.assertEqual(rows[0]["selection_probability"], 0.25)
        self.assertEqual(rows[0]["actual_selection_cost_bits"], 2.0)

    def test_cluster_draw_reproducibility(self):
        first = mechanism.cluster_draws(4, replicates=20, seed=99)
        second = mechanism.cluster_draws(4, replicates=20, seed=99)
        self.assertEqual(first, second)
        self.assertTrue(all(sum(row) == 4 for row in first))

    def test_zero_support_accounting(self):
        supported = mechanism.support_diagnostic([1.0] * 96, 4, 100)
        unsupported = mechanism.support_diagnostic([1.0] * 95, 5, 100)
        self.assertEqual((supported["valid"], supported["status"]), (96, "supported"))
        self.assertEqual((unsupported["valid"], unsupported["status"]), (95, "unsupported"))

    def test_weighted_quintile_mass_conservation(self):
        records = [
            mechanism.Record((1, 0), (1, 0), 1, 5, 0),
            mechanism.Record((0, 1), (0, 1), -1, 5, 5),
        ]
        values = [{"S_u1": 0.0}, {"S_u1": 1.0}]
        rows, cdf = mechanism.quintile_summary("toy", "S_u1", records, values, 1)
        self.assertAlmostEqual(sum(row["quintile_probability"] for row in rows), 1.0)
        for quintile in {row["quintile"] for row in rows}:
            self.assertEqual([row for row in cdf if row["quintile"] == quintile][-1]["conditional_cdf"], 1.0)

    def test_compact_cluster_probability_mass_conservation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mechanism_margin_by_key.csv"
            rows = ["feature_value,Nz,Ez"]
            rows.extend(f'K={key}|U=2.0|V=2.0|M=1,7,0' for key in range(128))
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            packed = mechanism.read_clustered_compact(path, 1, 1, 2)
            self.assertEqual(sum(packed[-2]), 128 * 7)
            self.assertEqual(sum(packed[-1]), 0)
            self.assertEqual(set(packed[-2]), {7})

    def test_chunked_gzip_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            logical = Path(directory) / "law.csv"
            archive = gzip.compress(b"a,b\n1,2\n", mtime=0)
            midpoint = len(archive) // 2
            (Path(str(logical) + ".gz.part000")).write_bytes(archive[:midpoint])
            (Path(str(logical) + ".gz.part001")).write_bytes(archive[midpoint:])
            with mechanism.open_text(logical) as handle:
                self.assertEqual(handle.read(), "a,b\n1,2\n")


if __name__ == "__main__":
    unittest.main()
