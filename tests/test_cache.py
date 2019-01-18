import httpretty
import json
import os
import pickle
import redis
import requests
import shutil
import struct
import time
import unittest
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.caches.redis_cache import RedisCache
from canonicalwebteam.http import CachedSession
from datetime import timedelta
from mockredis import mock_redis_client
from unittest.mock import patch


file_cache_directory = ".testcache"


class MockRedisSingleton:
    def __init__(self):
        self.redis_client = None

    def mock_redis_client_singleton(self, *args, **kwargs):
        if not self.redis_client:
            self.redis_client = mock_redis_client()
        return self.redis_client


class TestCachedSession(unittest.TestCase):
    mock_redis_singleton = MockRedisSingleton()

    def tearDown(self):
        try:
            shutil.rmtree(file_cache_directory)
        except:
            pass

    @httpretty.activate
    def test_custom_heuristic(self):
        def request_callback(request, uri, response_headers):
            return [200, response_headers, json.dumps({"epoch": time.time()})]

        httpretty.register_uri(
            httpretty.GET, "https://now.httpbin.org", body=request_callback
        )

        session = CachedSession(
            fallback_cache_duration=2,
            file_cache_directory=file_cache_directory,
        )

        # with a 2s retention, and a 1.1s time between requests, 2 of the
        # request should have the same epoch, where as the 3rd gets fresh data
        # the first requests gets send at t=0
        response = []

        for i in range(3):
            resp = session.get("https://now.httpbin.org")
            response.append(resp)
            time.sleep(1.1)

        self.assertEqual(response[0].text, response[1].text)
        self.assertNotEqual(response[1].text, response[2].text)

    @httpretty.activate
    def test_default_heuristic(self):
        def request_callback(request, uri, response_headers):
            return [200, response_headers, json.dumps({"epoch": time.time()})]

        httpretty.register_uri(
            httpretty.GET, "https://now.httpbin.org", body=request_callback
        )

        session = CachedSession(file_cache_directory=file_cache_directory)

        # with default 5s retention, and a 2.6s time between requests, 2 of the
        # request should have the same epoch, where as the 3rd gets fresh data
        # the first requests gets send at t=0
        response = []

        for i in range(3):
            resp = session.get("https://now.httpbin.org")
            response.append(resp)
            time.sleep(2.6)

        self.assertEqual(response[0].text, response[1].text)
        self.assertNotEqual(response[1].text, response[2].text)

    @httpretty.activate
    def test_cache_control_max_age_overwrites_custom_heuristic(self):
        def request_callback(request, uri, response_headers):
            return [200, response_headers, json.dumps({"epoch": time.time()})]

        httpretty.register_uri(
            httpretty.GET,
            "https://now.httpbin.org",
            body=request_callback,
            adding_headers={"Cache-Control": "max-age=3"},
        )

        session = CachedSession(file_cache_directory=file_cache_directory)

        # with 3s retention from CC, and a 1.6s time between requests, 2 of the
        # request should have the same epoch, where as the 3rd gets fresh data
        # the first requests gets send at t=0
        response = []

        for i in range(3):
            resp = session.get("https://now.httpbin.org")
            response.append(resp)
            time.sleep(1.6)

        self.assertEqual(response[0].text, response[1].text)
        self.assertNotEqual(response[1].text, response[2].text)

    @httpretty.activate
    def test_cache_control_no_cache_overwrites_custom_heuristic(self):
        def request_callback(request, uri, response_headers):
            return [200, response_headers, json.dumps({"epoch": time.time()})]

        httpretty.register_uri(
            httpretty.GET,
            "https://now.httpbin.org",
            body=request_callback,
            adding_headers={"Cache-Control": "no-cache"},
        )
        session = CachedSession(file_cache_directory=file_cache_directory)

        # with no-cache set, no request should be cached,
        # thus all bodies are different
        response = []

        for i in range(3):
            resp = session.get("https://now.httpbin.org")
            response.append(resp)

        self.assertNotEqual(response[0].text, response[1].text)
        self.assertNotEqual(response[1].text, response[2].text)

    @httpretty.activate
    def test_file_cache(self):
        epoch = time.time()
        httpretty.register_uri(
            httpretty.GET,
            "https://now.httpbin.org",
            body=json.dumps({"epoch": epoch}),
        )

        session = CachedSession(file_cache_directory=file_cache_directory)

        resp = session.get("https://now.httpbin.org")

        file_path = None

        if os.path.isfile(file_cache_directory):
            file_path = file_cache_directory
        else:
            for root, dirs, files in os.walk(file_cache_directory):
                if files:
                    file_path = (
                        root
                        + "/"
                        + files[
                            0
                        ]  # there can only be one cache file in this test.
                    )

        content = None

        with open(file_path, "rb") as file:
            content = file.read()

        self.assertNotEqual(file, None)
        self.assertIn(str(resp.text), str(content))

    @httpretty.activate
    @patch("redis.Redis", mock_redis_singleton.mock_redis_client_singleton)
    def test_redis_cache(self):
        redis_mock = redis.Redis()

        epoch = time.time()
        httpretty.register_uri(
            httpretty.GET,
            "https://now.httpbin.org",
            body=json.dumps({"epoch": epoch}),
            adding_headers={"Cache-Control": "max-age=300"},
        )

        session = CachedSession(redis_connection_pool=redis_mock)
        resp = session.get("https://now.httpbin.org")

        cursor, keys = redis_mock.scan()
        cached_response_key = keys[
            0
        ]  # we can expect that only one response was sent and cached

        cached_response = redis_mock.get(cached_response_key)
        self.assertIn(str(resp.text), str(cached_response))

        # Make sure not to mess with the byte structure here
        # replace with a same length string
        new_response = cached_response.replace(
            bytes("epoch", "utf-8"), bytes("qmaks", "utf-8")
        )
        redis_mock.set(cached_response_key, new_response)
        resp2 = session.get("https://now.httpbin.org")

        self.assertIn("qmaks", resp2.text)


if __name__ == "__main__":
    unittest.main()
