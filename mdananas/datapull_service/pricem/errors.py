import re
from urllib.parse import urlsplit, urlunsplit


class PayloadError(ValueError):
    """Invalid data. Retrying the same snapshot requires an explicit request."""


class ImportConfigurationError(RuntimeError):
    pass


class ImportLockLost(RuntimeError):
    """Transient SQL session loss; leave the durable run for the next tick."""


def safe_error(error):
    """HTTP errors can contain the secret export query string."""

    def strip_query(match):
        try:
            url = urlsplit(match.group(0))
            host = url.hostname or ""
            if url.port:
                host += f":{url.port}"
            return urlunsplit((url.scheme, host, url.path, "", ""))
        except ValueError:
            return "[URL redacted]"

    message = re.sub(r"https?://[^\s\"\'<>]+", strip_query, str(error))
    message = re.sub(
        r"(?i)\b(password|pwd|token|api[_-]?key)\s*[=:]\s*[^\s;,]+",
        r"\1=[redacted]",
        message,
    )
    return f"{type(error).__name__}: {message}"[:4000]
