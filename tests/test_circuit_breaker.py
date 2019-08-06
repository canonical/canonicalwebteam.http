import unittest
from unittest.mock import patch

from pybreaker import CircuitBreakerError
from requests.exceptions import HTTPError
from canonicalwebteam.http import BaseSession


def call_and_ignore_exceptions(fn, *args):
    try:
        fn(*args)
    except HTTPError:
        pass


class TestCircuitBreaker(unittest.TestCase):
    @patch("requests.Session.request")
    def test_circuit_opens(self, request_mock):
        request_mock.side_effect = HTTPError()
        session = BaseSession()

        for _ in range(4):
            call_and_ignore_exceptions(session.get, "https://httpbin.org")

        with self.assertRaises(CircuitBreakerError):
            session.get("https://httpbin.org")
