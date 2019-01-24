import calendar
from cachecontrol.heuristics import BaseHeuristic
from datetime import timedelta, datetime
from email.utils import formatdate


def expire_after(delta, date=None):
    date = date or datetime.utcnow()
    return date + delta


def datetime_to_header(dt):
    return formatdate(calendar.timegm(dt.timetuple()))


def cache_control_in_response_headers(headers):
    """
    Checks if CacheControl is set in response headers
    """
    cache_control = "cache-control" in headers
    pragma = "pragma" in headers and "no-cache" in headers["pragma"]
    expires = "expires" in headers


class ExpiresAfterIfNoCacheControl(BaseHeuristic):
    """
    Cache **all** requests for a defined time period.
    """

    def __init__(self, **kw):
        self.delta = timedelta(**kw)

    def update_headers(self, response):
        if cache_directives_in_headers(reponse.headers):
            return

        expires = expire_after(self.delta)

        return {
            "expires": datetime_to_header(expires),
            "cache-control": "public",
        }

    def warning(self):
        template = "110 - Automatically cached for %s. Response might be stale"
        return template % self.delta

    def apply(self, response):
        updated_headers = self.update_headers(response)

        if updated_headers:
            response.headers.update(updated_headers)
            warning_header_value = self.warning(response)
            if warning_header_value is not None:
                response.headers.update({"Warning": warning_header_value})

        return response
