# Core packages
import os
from urllib.parse import urlparse

# Third-party packages
import requests
import requests_cache

try:
    import prometheus_client
    timeout_counter = prometheus_client.Counter(
        'feed_timeouts',
        'A counter of timed out requests',
        ['domain'],
    )
    connection_failed_counter = prometheus_client.Counter(
        'feed_connection_failures',
        'A counter of requests which failed to connect',
        ['domain'],
    )
    latency_histogram = prometheus_client.Histogram(
        'feed_latency_seconds',
        'Feed requests retrieved',
        ['domain', 'code'],
        buckets=[0.25, 0.5, 0.75, 1, 2, 3],
    )
except ImportError:
    timeout_counter = None
    connection_failed_counter = None
    latency_histogram = None


class TimeoutHTTPAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, timeout=None, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, *args, **kwargs):
        kwargs['timeout'] = self.timeout
        return super().send(*args, **kwargs)


class BaseSession():
    """A base session interface to implement common functionality

    Create an interface to manage exceptions and return API exceptions
    """
    def __init__(self, timeout=(0.5, 3), *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mount("http://", TimeoutHTTPAdapter(timeout=timeout))
        self.mount("https://", TimeoutHTTPAdapter(timeout=timeout))

        # TODO allow user to choose it's own user agent
        storefront_header = 'storefront ({commit_hash};{environment})'.format(
            commit_hash=os.getenv('COMMIT_ID', 'commit_id'),
            environment=os.getenv('ENVIRONMENT', 'devel'),
        )

        headers = {
            'User-Agent': storefront_header,
        }
        self.headers.update(headers)

    def request(self, method, url, **kwargs):
        domain = urlparse(url).netloc

        try:
            request = super().request(method=method, url=url, **kwargs)
        except requests.exceptions.Timeout:
            if timeout_counter:
                timeout_counter.labels(domain=domain).inc()

            raise ApiTimeoutError(
                'The request to {} took too long'.format(url),
            )
        except requests.exceptions.ConnectionError:
            if connection_failed_counter:
                connection_failed_counter.labels(domain=domain).inc()

            raise ApiConnectionError(
                'Failed to establish connection to {}.'.format(url)
            )

        if latency_histogram:
            latency_histogram.labels(
                domain=domain, code=request.status_code
            ).observe(request.elapsed.total_seconds())

        return request


class UncachedSession(BaseSession, requests.Session):
    pass


class CachedSession(BaseSession, requests_cache.CachedSession):
    def __init__(
            self, *args,
            backend='sqlite', expire_after=5, include_get_headers=True,
            **kwargs
        ):

        super().__init__(
            *args,
            backend=backend, expire_after=expire_after,
            include_get_headers=include_get_headers,
            **kwargs
        )

