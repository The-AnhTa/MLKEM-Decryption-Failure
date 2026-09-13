import tempfile
import unittest
from pathlib import Path

import final_su1_confirmation as final


class FinalSu1ConfirmationTests(unittest.TestCase):
    def test_frozen_su1_computation(self):
        record = final.Record(0, 6, 2, 1, 0)
        self.assertEqual(final.score(record, 8, 29), 3 / 116)
        self.assertEqual(final.FROZEN_ORIENTATION, 1)

    def test_exact_cluster_mass_conservation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "law.csv"
            rows = ["feature_id,feature_value,Nz,Ez"]
            rows.extend(f'su1_margin_by_key,"K={key}|A=3|M=1",11,0' for key in range(128))
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            records = final.read_records(path, 8, 29)
            self.assertEqual(sum(record.total for record in records), 128 * 11)
            self.assertEqual(sum(record.failures for record in records), 0)

    def test_bootstrap_is_deterministic(self):
        self.assertEqual(final.cluster_draws(4, 20, 99), final.cluster_draws(4, 20, 99))
        self.assertTrue(all(sum(row) == 4 for row in final.cluster_draws(4, 20, 99)))

    def test_preregistration_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preregistration.json"
            final.write_immutable(path, "frozen\n")
            final.write_immutable(path, "frozen\n")
            with self.assertRaises(ValueError):
                final.write_immutable(path, "changed\n")

    def test_actual_selection_cost(self):
        self.assertEqual(final.actual_selection_cost(0.25), 2.0)
        with self.assertRaises(ValueError):
            final.actual_selection_cost(0.0)

    def test_zero_support_accounting(self):
        self.assertEqual(final.support_status(1000), (0.1, "SUPPORTED"))
        self.assertEqual(final.support_status(1001), (0.1001, "UNSUPPORTED"))


if __name__ == "__main__":
    unittest.main()
