import math
import unittest

import key_hazard_decomposition as kh


class KeyHazardTests(unittest.TestCase):
    def setUp(self):
        self.executions = [
            (0, .1, 2, 3, 0), (0, .4, -1, 1, 1),
            (1, .2, 1, 2, 0), (1, .6, -2, 2, 2),
        ]
        self.coordinates = [
            (0, .1, 2, 3, 0), (0, .3, 1, 3, 0),
            (0, .4, -1, 1, 1), (0, .2, 2, 1, 0),
            (1, .2, 1, 2, 0), (1, .4, 2, 2, 0),
            (1, .6, -2, 2, 2), (1, .5, 1, 2, 0),
        ]

    def test_covariance_decomposition_identity_and_conditional_means(self):
        keys, stats, _ = kh.execution_key_stats(self.executions)
        total, within, between = kh.covariance_terms(stats)
        self.assertEqual(keys, [0, 1])
        self.assertAlmostEqual(total, within + between, places=15)
        self.assertAlmostEqual(stats[0][1] / stats[0][0], .175)
        self.assertAlmostEqual(stats[1][2] / stats[1][0], .5)

    def test_coordinate_mass_and_local_indicator(self):
        _, estats, _ = kh.execution_key_stats(self.executions)
        _, lstats = kh.local_key_stats(self.coordinates)
        self.assertEqual([row[0] for row in lstats], [2 * row[0] for row in estats])
        for _, _, margin, total, failures in self.coordinates:
            self.assertEqual(margin <= 0, failures == total)

    def test_global_failure_is_any_coordinate_failure(self):
        cases = [([3, 1, 4], False), ([3, 0, 4], True), ([-1, 2, 3], True)]
        for margins, failed in cases:
            self.assertEqual(min(margins) <= 0, failed)
            self.assertEqual(any(value <= 0 for value in margins), failed)

    def test_cluster_bootstrap_is_deterministic(self):
        _, estats, _ = kh.execution_key_stats(self.executions)
        _, lstats = kh.local_key_stats(self.coordinates)
        first = kh.bootstrap(estats, lstats, replicates=40, seed=17)
        second = kh.bootstrap(estats, lstats, replicates=40, seed=17)
        self.assertEqual(first, second)

    def test_key_centering_zero_weighted_mean(self):
        for key in (0, 1):
            rows = [row for row in self.coordinates if row[0] == key]
            mass = sum(row[3] for row in rows)
            mean_x = sum(row[1] * row[3] for row in rows) / mass
            mean_m = sum(row[2] * row[3] for row in rows) / mass
            self.assertAlmostEqual(sum((row[1] - mean_x) * row[3] for row in rows), 0)
            self.assertAlmostEqual(sum((row[2] - mean_m) * row[3] for row in rows), 0)

    def test_exact_support_hazard_mass_conservation(self):
        rows = kh.local_hazard(self.coordinates)
        self.assertEqual(sum(row["coordinate_mass"] for row in rows),
                         sum(row[3] for row in self.coordinates))
        self.assertEqual(sorted(row["x"] for row in rows), [.1, .2, .3, .4, .5, .6])


if __name__ == "__main__":
    unittest.main()
