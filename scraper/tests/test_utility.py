"""
Test suite for utility functions (test_utility.py).

Includes unit tests for parse_time and split_event from src.utility.
"""

import unittest
import pandas as pd
import pandas.testing as pdt

from src.utility import parse_time, split_event


class TestUtilityFunctions(unittest.TestCase):
    """
    Test suite for utility.py functions.

    Contains tests for parse_time and split_event functionalities.
    """

    def test_parse_time_hms(self):
        """
        Test parse_time with an 'H:MM:SS' formatted string (1:02:03).

        Expects the total seconds to be (1 hour * 3600) + (2 minutes * 60) +
        3 seconds = 3723.
        """
        self.assertAlmostEqual(parse_time("1:02:03"), 3723.0)

    def test_parse_time_ms(self):
        """
        Test parse_time with an 'MM:SS' formatted string (02:30).

        Expects 2 minutes 30 seconds = 150.0 seconds.
        """
        self.assertAlmostEqual(parse_time("02:30"), 150.0)

    def test_parse_time_decimal(self):
        """
        Test parse_time with a simple decimal string (2.5).

        Expects 2.5 seconds.
        """
        self.assertAlmostEqual(parse_time("2.5"), 2.5)

    def test_parse_time_with_trailing_M(self):
        """
        Test parse_time with a trailing 'M' (02:30M).

        Expects it to ignore the 'M' and parse as 150.0 seconds.
        """
        self.assertAlmostEqual(parse_time("02:30M"), 150.0)

    def test_parse_time_with_whitespace(self):
        """
        Test parse_time with leading/trailing whitespace around an
        'H:MM:SS' string.

        Expects 1 hour + 1 minute + 1 second = 3661 seconds.
        """
        self.assertAlmostEqual(parse_time("  01:01:01  "), 3661.0)

    def test_split_event_standard(self):
        """
        Test split_event with a standard event string (100m Butterfly).

        Expects distance=100, style="Butterfly".
        """
        result = split_event("100m Butterfly")
        expected = pd.Series({"distance": 100, "style": "Butterfly"})
        pdt.assert_series_equal(result, expected)

    def test_split_event_extra_spaces(self):
        """
        Test split_event with extra spaces (  200m   Freestyle  ).

        Expects distance=200, style="Freestyle".
        """
        result = split_event("  200m   Freestyle  ")
        expected = pd.Series({"distance": 200, "style": "Freestyle"})
        pdt.assert_series_equal(result, expected)

    def test_split_event_missing_style(self):
        """
        Test split_event with only the distance (400m).

        Expects distance=400, style="".
        """
        result = split_event("400m ")
        expected = pd.Series({"distance": 400, "style": ""})
        pdt.assert_series_equal(result, expected)

    def test_split_event_invalid_format(self):
        """
        Test split_event with an invalid format (no distance, e.g.,
        "Freestyle").

        Expects distance=None, style=None.
        """
        result = split_event("Freestyle")
        expected = pd.Series({"distance": None, "style": None})
        pdt.assert_series_equal(result, expected)


if __name__ == '__main__':
    unittest.main()
