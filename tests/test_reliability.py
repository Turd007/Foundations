import unittest
from foundations_bridge.reliability import ReliabilityTracker

class TestReliability(unittest.TestCase):
    def test_basic(self):
        tr = ReliabilityTracker()
        self.assertEqual(tr.rolling(), 0.0)
        tr.record(True); tr.record(True); tr.record(False)
        self.assertAlmostEqual(tr.rolling(), 2/3, places=6)

if __name__ == "__main__":
    unittest.main()
