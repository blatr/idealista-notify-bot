from urllib.parse import urlsplit, urlunsplit


def strip_ru_prefix(url: str) -> str:
    """Remove '/ru' prefix from Idealista URLs if present."""
    if not url:
        return url

    parts = urlsplit(url.strip())
    path = parts.path or "/"

    if path == "/ru":
        path = "/"
    elif path.startswith("/ru/"):
        path = path[len("/ru"):]

    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
