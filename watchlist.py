import logging
import os

from config import DATA_DIR, IDEALISTA_URL, WATCH_URLS_FILE

logger = logging.getLogger(__name__)


def load_watch_urls() -> set[str]:
    """Load watch URLs from disk, always including IDEALISTA_URL if set."""
    urls: set[str] = set()
    if IDEALISTA_URL:
        urls.add(IDEALISTA_URL)

    if os.path.exists(WATCH_URLS_FILE):
        try:
            with open(WATCH_URLS_FILE, "r", encoding="utf-8") as handle:
                for line in handle:
                    url = line.strip()
                    if url:
                        urls.add(url)
        except Exception as exc:
            logger.error(f"Failed to load watch URLs: {exc}")

    return urls


def save_watch_urls(urls: set[str]) -> None:
    """Persist watch URLs to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        with open(WATCH_URLS_FILE, "w", encoding="utf-8") as handle:
            for url in sorted(urls):
                handle.write(url + "\n")
    except Exception as exc:
        logger.error(f"Failed to save watch URLs: {exc}")


def add_watch_url(urls: set[str], url: str) -> bool:
    """Add a watch URL if new. Returns True when added."""
    normalized = url.strip()
    if not normalized:
        return False

    if normalized in urls:
        return False

    urls.add(normalized)
    save_watch_urls(urls)
    return True
