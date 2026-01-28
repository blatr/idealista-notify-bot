import re
from bs4 import BeautifulSoup
from scrapfly import ScrapflyClient, ScrapeConfig
from webapp.config import SCRAPFLY_API_KEY

scrapfly = ScrapflyClient(key=SCRAPFLY_API_KEY)


def parse_price(price_text: str) -> tuple[str, float]:
    """Parse price string to formatted string and numeric value."""
    if not price_text:
        return "N/A", 0.0

    # Remove currency symbol and clean up
    cleaned = price_text.replace("€", "").replace("/mes", "").strip()
    # Remove thousand separators
    cleaned = cleaned.replace(".", "").replace(",", "")

    try:
        # Extract first number
        numbers = re.findall(r"\d+", cleaned)
        if numbers:
            price_value = float(numbers[0])
            # Format nicely
            price_str = f"{int(price_value):,}".replace(",", " ") + " EUR"
            return price_str, price_value
    except (ValueError, IndexError):
        pass

    return price_text, 0.0


async def parse_idealista_url(url: str) -> dict:
    """
    Fetch and parse a single Idealista listing URL.
    Returns dict with listing fields.
    """
    if not url or "idealista.com" not in url:
        raise ValueError("Invalid Idealista URL")

    result = scrapfly.scrape(
        ScrapeConfig(
            url=url,
            asp=True,
            country="ES",
            render_js=True,
        )
    )

    if not result.success:
        raise Exception(f"Failed to fetch URL: {result.upstream_status_code}")

    soup = BeautifulSoup(result.content, "html.parser")

    # Parse individual listing page structure
    # Title
    title_el = soup.find("span", class_="main-info__title-main")
    title = title_el.get_text(strip=True) if title_el else "Unknown"

    # Price
    price_el = soup.find("span", class_="info-data-price")
    price_text = price_el.get_text(strip=True) if price_el else ""
    price, price_value = parse_price(price_text)

    # Features (rooms, size)
    rooms = ""
    size = ""
    features = soup.find("div", class_="info-features")
    if features:
        spans = features.find_all("span")
        for span in spans:
            text = span.get_text(strip=True).lower()
            if "hab" in text:
                rooms = span.get_text(strip=True)
            elif "m²" in text or "m2" in text:
                size = span.get_text(strip=True)

    # Floor
    floor = ""
    details_section = soup.find("section", class_="details-property")
    if details_section:
        floor_el = details_section.find(string=re.compile(r"planta", re.I))
        if floor_el:
            floor = floor_el.strip()

    # Description
    description = ""
    comment_div = soup.find("div", class_="comment")
    if comment_div:
        # Get text content, limit length
        description = comment_div.get_text(strip=True)[:500]

    # Thumbnail
    thumbnail = ""
    img_el = soup.find("img", class_="image-focus")
    if img_el and img_el.get("src"):
        thumbnail = img_el["src"]
    else:
        # Try other image selectors
        gallery_img = soup.select_one(".detail-image-gallery img")
        if gallery_img and gallery_img.get("src"):
            thumbnail = gallery_img["src"]

    return {
        "title": title,
        "price": price,
        "price_value": price_value,
        "rooms": rooms,
        "size": size,
        "floor": floor,
        "description": description,
        "thumbnail": thumbnail,
        "idealista_url": url,
    }


class ScraperService:
    """Service wrapper for scraping operations."""

    @staticmethod
    async def parse_url(url: str) -> dict:
        """Parse an Idealista listing URL."""
        return await parse_idealista_url(url)
