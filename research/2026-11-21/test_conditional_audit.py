import unittest
import numpy as np
from pathlib import Path
import importlib.util

p = Path(__file__).with_name("conditional_audit.py")
spec = importlib.util.spec_from_file_location("conditional_audit", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestConditionalAudit(unittest.TestCase):
    def test_perfect_detection(self):
        a = m.threshold_curve([.1,.9], [False,True], [.5])
        np.testing.assert_allclose(a[0,:2], [1,1])

    def test_core_cost(self):
        a = m.threshold_curve([.8,.9], [False,True], [.5], [True,False])
        self.assertEqual(a[0,2], 1)

    def test_empty_prediction(self):
        a = m.threshold_curve([.1,.2], [False,True], [1])
        self.assertTrue(np.isnan(a[0,0]))
        self.assertEqual(a[0,1], 0)

    def test_cluster_reproducible(self):
        x = m.image_cluster_bootstrap([1,1,3,3], [0,0,1,1], seed=12)
        np.testing.assert_array_equal(x, m.image_cluster_bootstrap([1,1,3,3], [0,0,1,1], seed=12))
        self.assertTrue(x[0] <= 2 <= x[-1])

    def test_one_cluster_rejected(self):
        with self.assertRaises(ValueError):
            m.image_cluster_bootstrap([1,2], [0,0])


if __name__ == "__main__":
    unittest.main()
