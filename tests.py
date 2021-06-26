import unittest
import interleave


class InterleavingTests(unittest.TestCase):
    def test_single_sync_point(self):
        sections = interleave.create_sections_from_sync_points(["4:16"], 183, 373)
        self.assertEqual(len(sections), 2)

    def test_multiple_sync_points(self):
        sections = interleave.create_sections_from_sync_points(["4:16","51:101","99:212","140:297"], 183, 373)
        self.assertEqual(len(sections), 5)

if __name__ == '__main__':
    unittest.main()
