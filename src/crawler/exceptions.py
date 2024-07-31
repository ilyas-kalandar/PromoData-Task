class CrawlerError(Exception):
    """Base for all errors"""


class PageNotFound(CrawlerError):
    """If page not found."""


class IPAddressBlocked(CrawlerError):
    """If our IP is blocked by server."""
