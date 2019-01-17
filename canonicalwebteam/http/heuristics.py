import calendar
from cachecontrol.heuristics import BaseHeuristic
from datetime import timedelta, datetime
from email.utils import formatdate


def expire_after(delta, date=None):
    date = date or datetime.utcnow()
    return date + delta


def datetime_to_header(dt):
    return formatdate(calendar.timegm(dt.timetuple()))


def cache_control_value_present_in_response(headers, type):
    """
    checks if a certain CacheControl header is set in the headers
    """
    return "cache-control" in headers and type in headers["cache-control"]


class ExpiresAfterIfNoCacheControl(BaseHeuristic):
    """
    Cache **all** requests for a defined time period.
    """

    def __init__(self, **kw):
        self.delta = timedelta(**kw)

    def update_headers(self, response):
        def cc_value_in_response_headers(type):
            return cache_control_value_present_in_response(
                response.headers, type
            )

        if cc_value_in_response_headers(
            "no-cache"
        ) or cc_value_in_response_headers("max-age"):
            return None

        expires = expire_after(self.delta)

        return {
            "expires": datetime_to_header(expires),
            "cache-control": "public",
        }

    def warning(self, response):
        tmpl = "110 - Automatically cached for %s. Response might be stale"
        return tmpl % self.delta

    def apply(self, response):
        updated_headers = self.update_headers(response)

        if updated_headers:
            response.headers.update(updated_headers)
            warning_header_value = self.warning(response)
            if warning_header_value is not None:
                response.headers.update({"Warning": warning_header_value})

        return response
