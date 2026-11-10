import unittest
from component_audit_20261110 import components, protected_mask_cost


class ComponentAuditTests(unittest.TestCase):
    def test_diagonal_is_disconnected(self):
        self.assertEqual(components([[1,0],[0,1]]), [1,1])

    def test_connected_cross(self):
        self.assertEqual(components([[0,1,0],[1,1,1],[0,1,0]]), [5])

    def test_empty_components(self):
        self.assertEqual(components([[0,0]]), [])

    def test_invalid_shape(self):
        with self.assertRaises(ValueError):
            components([[1],[0,1]])

    def test_cost_breakdown(self):
        self.assertEqual(
            protected_mask_cost([[0,1,1]], [[1,0,0]], [[0,1,0]], 4),
            {"missed_cr":1,"false_background":1,"false_core":1,"weighted_cost":6},
        )

    def test_overlapping_truth_rejected(self):
        with self.assertRaises(ValueError):
            protected_mask_cost([[1]], [[1]], [[1]])


if __name__ == "__main__":
    unittest.main()
