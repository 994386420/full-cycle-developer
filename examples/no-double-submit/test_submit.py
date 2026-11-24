import unittest

from submit import SubmitController


class SubmitTests(unittest.TestCase):
    def test_duplicate_submit(self):
        requests = []
        controller = SubmitController(requests.append)

        self.assertTrue(controller.submit())
        self.assertFalse(controller.submit())
        self.assertEqual(len(requests), 1)

    def test_submit_again_after_completion(self):
        requests = []
        controller = SubmitController(requests.append)

        self.assertTrue(controller.submit())
        requests[0]()
        self.assertTrue(controller.submit())
        self.assertEqual(len(requests), 2)
