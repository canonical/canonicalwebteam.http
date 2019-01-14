import redis
import unittest
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.caches.redis_cache import RedisCache
from canonicalwebteam.http import CachedSession
from datetime import timedelta
from unittest import TestCase


def create_redis_connection_pool(
    redis_port="6379", redis_host="localhost", redis_db=0
):
    return redis.ConnectionPool(host=redis_host, port=redis_port, db=redis_db)


class TestCachedSession(TestCase):
    def test_custom_heuristic(self):
        session = CachedSession(fallback_cache_duration=10)
        adapter = session.get_adapter("http://")
        heuristic = adapter.heuristic
        delta = heuristic.delta
        self.assertEqual(delta, timedelta(seconds=10))

    def test_default_heuristic(self):
        session = CachedSession()
        adapter = session.get_adapter("http://")
        heuristic = adapter.heuristic
        delta = heuristic.delta
        self.assertEqual(delta, timedelta(seconds=5))

    def test_file_cache(self):
        session = CachedSession()
        adapter = session.get_adapter("http://")
        cache = adapter.cache
        self.assertIsInstance(cache, FileCache)

    def test_redis_cache(self):
        pool = create_redis_connection_pool()
        session = CachedSession(redis_cache_pool=pool)
        adapter = session.get_adapter("http://")
        cache = adapter.cache
        self.assertIsInstance(cache, RedisCache)


if __name__ == "__main__":
    unittest.main()
