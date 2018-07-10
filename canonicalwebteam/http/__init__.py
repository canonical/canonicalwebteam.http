# Core packages
from urllib.parse import urlparse

# Third-party packages
import requests
import requests_cache

try:
    # If prometheus is available, set up metric counters

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
    """
    A simple extension to the HTTPAdapter to add a 'timeout' parameter
    """

    def __init__(self, timeout=None, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, *args, **kwargs):
        kwargs['timeout'] = self.timeout
        return super().send(*args, **kwargs)


class BaseSession():
    """
    A base session interface to implement common functionality:

    - timeout: Set timeout for outgoing requests
    - headers: Additional headers to add to all outgoing requests
    """

    def __init__(self, timeout=(0.5, 3), headers={}, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mount("http://", TimeoutHTTPAdapter(timeout=timeout))
        self.mount("https://", TimeoutHTTPAdapter(timeout=timeout))

        self.headers.update(headers)

    def request(self, method, url, **kwargs):
        request = super().request(method=method, url=url, **kwargs)

        if latency_histogram:
            latency_histogram.labels(
                domain=urlparse(url).netloc, code=request.status_code
            ).observe(request.elapsed.total_seconds())

        return request


class UncachedSession(BaseSession, requests.Session):
    """
    A session object for making HTTP requests directly, using the default
    settings from BaseSession
    """

    pass


class CachedSession(BaseSession, requests_cache.CachedSession):
    """
    A session object for making HTTP requests with cached responses.

    Responses for an identical request will be naively returned from the
    cache if the cached copy if less than "expire_after" seconds old.
    """

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
