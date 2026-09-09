import unittest
from contextlib import redirect_stdout
from io import StringIO

from scripts.run_end_to_end import main


class EndToEndTests(unittest.TestCase):
    def test_complete_offline_pipeline_succeeds(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
