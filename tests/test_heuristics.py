import locale
import unittest
from datetime import datetime, timedelta

from canonicalwebteam.http import heuristics


class TestHeuristics(unittest.TestCase):
    def test_custom_heuristic(self):
        today = datetime.utcnow()
        one_day_delta = timedelta(days=1)
        tomorrow = today + one_day_delta

        self.assertEqual(
            tomorrow, heuristics.expire_after(one_day_delta, today)
        )

    def test_datetime_to_header_string(self):
        locale.setlocale(locale.LC_ALL, "en_GB.utf8")
        date_string = "Thu, 01 Dec 1994 16:00:00 GMT"
        date = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %Z")

        self.assertEqual(date_string, heuristics.datetime_to_HTTP_date(date))

    def test_cache_directives_in_headers(self):
        headers = {}

        self.assertEqual(
            heuristics.cache_directives_in_headers(headers), False
        )

        headers = {"expires": "1"}

        self.assertEqual(heuristics.cache_directives_in_headers(headers), True)

        headers = {"pragma": "no-cache"}

        self.assertEqual(heuristics.cache_directives_in_headers(headers), True)

        headers = {"cache-control": "yeah"}

        self.assertEqual(heuristics.cache_directives_in_headers(headers), True)
