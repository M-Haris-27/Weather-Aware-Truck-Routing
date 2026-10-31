"""Exceptions shared by the services, pipeline and API layers."""


class InputError(Exception):
    """The request can't be fulfilled as given (maps to HTTP 400)."""


class NoRouteError(InputError):
    """No drivable route exists between the two places."""


class UpstreamError(Exception):
    """A third-party API failed or returned something unusable (maps to HTTP 502)."""


class ConfigError(Exception):
    """The server is missing configuration, e.g. an API key (maps to HTTP 503)."""
