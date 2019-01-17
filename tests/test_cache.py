import httpretty
import json
import redis
import shutil
import time
import unittest
import requests
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.caches.redis_cache import RedisCache
from canonicalwebteam.http import CachedSession
from datetime import timedelta

file_cache_directory = ".testcache"


def create_redis_connection_pool(
    redis_port="6379", redis_host="localhost", redis_db=0
):
    return redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db)


class TestCachedSession(unittest.TestCase):
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

    # def test_file_cache(self):
    #     session = CachedSession()
    #     adapter = session.get_adapter("http://")
    #     cache = adapter.cache
    #     self.assertIsInstance(cache, FileCache)

    # def test_redis_cache(self):
    #     pool = create_redis_connection_pool()
    #     session = CachedSession(redis_cache_pool=pool)
    #     adapter = session.get_adapter("http://")
    #     cache = adapter.cache
    #     self.assertIsInstance(cache, RedisCache)


if __name__ == "__main__":
    unittest.main()
