"""Idealista scraper using Scrapfly for anti-bot bypass."""

import logging
import os
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from scrapfly import ScrapflyClient, ScrapeConfig

from config import (
    DATA_DIR,
    EXCLUDED_AREAS,
    EXCLUDED_FLOORS,
    EXCLUDED_TERMS,
    IDEALISTA_URL,
    SCRAPFLY_API_KEY,
    SEEN_LISTINGS_FILE,
)
from idealista.url_utils import strip_ru_prefix

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Scrapfly client
scrapfly = ScrapflyClient(key=SCRAPFLY_API_KEY)

# In-memory cache of seen URLs (loaded from file on first use)
_seen_urls: set | None = None


def _infer_scrapfly_country_and_base(url: str) -> tuple[str, str]:
    """Infer Scrapfly country code and base URL from a full Idealista URL."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""

    if "idealista.com" in host:
        return "ES", base or "https://www.idealista.com"

    return "ES", base or "https://www.idealista.com"


def _build_pagination_url(base_url: str, page: int) -> str:
    """Build pagination URL preserving query string."""
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    if "/pagina-" in path:
        path = path.rsplit("/pagina-", 1)[0]
    paginated_path = f"{path}/pagina-{page}.htm"
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            paginated_path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


@dataclass
class Listing:
    """Represents a property listing."""
    url: str
    title: str
    price: str
    price_value: float
    rooms: str
    size: str
    floor: str
    description: str
    thumbnail: str = ""
    telephone: str = ""


def load_seen_listings() -> set:
    """Load seen URLs from text file into memory."""
    global _seen_urls

    if _seen_urls is not None:
        return _seen_urls

    _seen_urls = set()

    if os.path.exists(SEEN_LISTINGS_FILE):
        try:
            with open(SEEN_LISTINGS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url:
                        _seen_urls.add(url)
            logger.info(f"Loaded {len(_seen_urls)} seen URLs from {SEEN_LISTINGS_FILE}")
        except Exception as e:
            logger.error(f"Error loading seen listings: {e}")

    return _seen_urls


def save_seen_listings() -> None:
    """Save seen URLs from memory to text file."""
    global _seen_urls

    if _seen_urls is None:
        return

    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        with open(SEEN_LISTINGS_FILE, "w", encoding="utf-8") as f:
            for url in _seen_urls:
                f.write(url + "\n")
        logger.info(f"Saved {len(_seen_urls)} seen URLs to {SEEN_LISTINGS_FILE}")
    except Exception as e:
        logger.error(f"Error saving seen listings: {e}")


def add_seen_url(url: str) -> None:
    """Add a URL to the seen set and save to file."""
    global _seen_urls

    if _seen_urls is None:
        load_seen_listings()

    _seen_urls.add(url)
    save_seen_listings()


def _parse_price(price_text: str) -> tuple[str, float]:
    """Parse price text into formatted string and numeric value."""
    if not price_text:
        return "N/A", 0.0

    clean = price_text.replace("€", "").replace(".", "").replace(",", ".").split('/')[0].strip()
    try:
        value = float(clean.split()[0])
        formatted = f"{value:,.0f} €".replace(",", " ")
        return formatted, value
    except (ValueError, IndexError):
        return price_text, 0.0


def _should_exclude(listing: Listing) -> bool:
    """Check if listing should be excluded based on filters."""
    text = f"{listing.title} {listing.description}".lower()

    for area in EXCLUDED_AREAS:
        if area.lower() in text:
            return True

    for term in EXCLUDED_TERMS:
        if term.lower() in text:
            return True

    floor_text = listing.floor.lower()
    for floor in EXCLUDED_FLOORS:
        if floor.lower() in floor_text:
            return True

    return False


def _parse_listing(article, base_url: str) -> Listing | None:
    """Parse a single listing article."""
    try:
        # Link and title
        link_elem = article.find("a", class_="item-link")
        if not link_elem:
            return None

        href = link_elem.get("href", "")
        if not href:
            return None
        href = urljoin(base_url, href)
        href = strip_ru_prefix(href)

        title = link_elem.get_text(strip=True)

        # Price
        price_elem = article.find("span", class_="item-price")
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        price_formatted, price_value = _parse_price(price_text)

        # Details
        details = article.find_all("span", class_="item-detail")
        rooms = details[0].get_text(strip=True) if len(details) > 0 else "N/A"
        size = details[1].get_text(strip=True) if len(details) > 1 else "N/A"
        floor = details[2].get_text(strip=True) if len(details) > 2 else "N/A"

        # Description
        desc_elem = article.find("div", class_="item-description")
        if not desc_elem:
            desc_elem = article.find("div", class_="description")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Thumbnail
        img_elem = article.find("img")
        thumbnail = ""
        if img_elem:
            thumbnail = img_elem.get("src") or img_elem.get("data-src") or ""

        return Listing(
            url=href,
            title=title,
            price=price_formatted,
            price_value=price_value,
            rooms=rooms,
            size=size,
            floor=floor,
            description=description,
            thumbnail=thumbnail,
        )
    except Exception as e:
        logger.debug(f"Error parsing listing: {e}")
        return None


def scrape_listings(url: str = None) -> tuple[list[Listing], bool]:
    """
    Scrape Idealista listings using Scrapfly.

    Args:
        url: Optional custom URL to scrape

    Returns:
        Tuple of (list of new Listing objects, error_occurred flag)
    """
    url = url or IDEALISTA_URL
    country_code, base_url = _infer_scrapfly_country_and_base(url)
    logger.info(f"Scraping: {url}")

    try:
        result = scrapfly.scrape(
            ScrapeConfig(
                url=url,
                asp=True,  # Anti Scraping Protection
                country=country_code,
                render_js=True,
            )
        )
    except Exception as e:
        logger.error(f"Scrapfly request failed: {e}")
        return [], True

    if not result.success:
        logger.error(f"Scrape failed: {result.upstream_status_code}")
        return [], True

    logger.info(f"Got {len(result.content)} chars, status {result.upstream_status_code}")

    # Parse HTML
    soup = BeautifulSoup(result.content, "html.parser")

    # Find listings
    articles = soup.find_all("article", class_="item")
    if not articles:
        articles = soup.find_all("article")
        logger.info(f"No 'article.item' elements found, using all articles: {len(articles)}")
    else:
        logger.info(f"Found {len(articles)} listing elements")

    new_listings = []

    for article in articles:
        listing = _parse_listing(article, base_url)
        if not listing:
            continue

        # Apply filters
        if _should_exclude(listing):
            continue

        new_listings.append(listing)

    logger.info(f"Found {len(new_listings)} new listings")

    return new_listings, False


def scrape_all_pages(
    base_url: str = None,
    max_pages: int = 3,
    min_new_to_continue: int = 25,
    dedupe_fn=None,
) -> tuple[list[Listing], bool]:
    """
    Scrape multiple pages of listings.

    Args:
        base_url: Base search URL
        max_pages: Maximum number of pages to scrape
        min_new_to_continue: Only continue pagination if page has more than this count
        dedupe_fn: Optional callback to filter out already-known listings per page

    Returns:
        Tuple of (list of all new listings found, error_occurred flag)
    """
    base_url = base_url or IDEALISTA_URL
    all_listings: list[Listing] = []
    error_occurred = False

    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            url = _build_pagination_url(base_url, page)

        logger.info(f"Scraping page {page}: {url}")
        listings, error = scrape_listings(url)

        if error:
            logger.warning(f"Error on page {page}, stopping pagination")
            error_occurred = True
            break

        if dedupe_fn:
            try:
                listings = dedupe_fn(listings)
            except Exception as exc:
                logger.error(f"Failed to dedupe listings: {exc}")

        all_listings.extend(listings)

        if len(listings) <= min_new_to_continue:
            logger.info(
                f"{len(listings)} new listings on page {page} "
                f"(<= {min_new_to_continue}), stopping pagination"
            )
            break

    return all_listings, error_occurred


def clear_seen_listings() -> None:
    """Clear the seen listings cache."""
    global _seen_urls

    if os.path.exists(SEEN_LISTINGS_FILE):
        os.remove(SEEN_LISTINGS_FILE)

    _seen_urls = set()
    logger.info("Cleared seen listings cache")
