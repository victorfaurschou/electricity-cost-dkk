"""Shared error handling for upstream API calls."""

import requests

STATUS_MESSAGES = {
    401: "invalid or expired credentials",
    403: "access denied",
    429: "rate limited",
}


class UpstreamError(Exception):
    """A known, specific failure reported by an upstream API."""


def check_response(response: requests.Response, service: str) -> None:
    if response.ok:
        return
    code = response.status_code
    if code in STATUS_MESSAGES:
        raise UpstreamError(f"{service}: {STATUS_MESSAGES[code]}")
    if 500 <= code < 600:
        raise UpstreamError(f"{service} service error (HTTP {code})")
    raise UpstreamError(f"{service} returned HTTP {code}")
