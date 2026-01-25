"""Idealista Official API client.

To get credentials, apply at: https://developers.idealista.com/access-request
"""

import base64
import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "https://api.idealista.com/3.5"
TOKEN_URL = "https://api.idealista.com/oauth/token"


@dataclass
class Property:
    """Represents a property listing from the API."""
    property_code: str
    url: str
    title: str
    price: float
    price_formatted: str
    rooms: int
    size: float
    floor: str
    description: str
    thumbnail: str
    address: str
    municipality: str
    province: str
    operation: str
    property_type: str


class IdealistaAPI:
    """Client for the official Idealista API."""

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the API client.

        Args:
            api_key: Your Idealista API key
            api_secret: Your Idealista API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self._access_token: Optional[str] = None

    def _get_access_token(self) -> str:
        """Get OAuth2 access token."""
        if self._access_token:
            return self._access_token

        # Encode credentials
        credentials = f"{self.api_key}:{self.api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "read",
        }

        response = requests.post(TOKEN_URL, headers=headers, data=data)

        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")

        token_data = response.json()
        self._access_token = token_data["access_token"]
        logger.info("Successfully obtained access token")

        return self._access_token

    def search(
        self,
        country: str = "pt",
        operation: str = "sale",
        property_type: str = "homes",
        location_id: str = None,
        center: str = None,
        distance: int = None,
        min_price: int = None,
        max_price: int = None,
        min_size: int = None,
        max_size: int = None,
        bedrooms: list[int] = None,
        order: str = "publicationDate",
        sort: str = "desc",
        max_items: int = 50,
        num_page: int = 1,
    ) -> dict:
        """
        Search for properties.

        Args:
            country: Country code (es, pt, it)
            operation: sale or rent
            property_type: homes, offices, premises, garages, bedrooms
            location_id: Idealista location ID (e.g., "0-EU-PT-11-06")
            center: Coordinates for radius search (lat,lon)
            distance: Radius in meters (requires center)
            min_price: Minimum price
            max_price: Maximum price
            min_size: Minimum size in m²
            max_size: Maximum size in m²
            bedrooms: List of bedroom counts [1, 2, 3]
            order: Sort field (publicationDate, price, size, etc.)
            sort: Sort direction (asc, desc)
            max_items: Results per page (max 50)
            num_page: Page number

        Returns:
            API response dict with 'elementList', 'total', 'totalPages', etc.
        """
        token = self._get_access_token()

        url = f"{API_BASE_URL}/{country}/search"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Build parameters
        params = {
            "operation": operation,
            "propertyType": property_type,
            "order": order,
            "sort": sort,
            "maxItems": max_items,
            "numPage": num_page,
        }

        if location_id:
            params["locationId"] = location_id
        if center:
            params["center"] = center
        if distance:
            params["distance"] = distance
        if min_price:
            params["minPrice"] = min_price
        if max_price:
            params["maxPrice"] = max_price
        if min_size:
            params["minSize"] = min_size
        if max_size:
            params["maxSize"] = max_size
        if bedrooms:
            params["bedrooms"] = ",".join(map(str, bedrooms))

        response = requests.post(url, headers=headers, data=params)

        if response.status_code != 200:
            raise Exception(f"Search failed: {response.status_code} - {response.text}")

        return response.json()

    def search_properties(self, **kwargs) -> list[Property]:
        """
        Search and return Property objects.

        Same arguments as search().

        Returns:
            List of Property objects
        """
        data = self.search(**kwargs)
        properties = []

        for item in data.get("elementList", []):
            prop = Property(
                property_code=str(item.get("propertyCode", "")),
                url=item.get("url", ""),
                title=item.get("suggestedTexts", {}).get("title", ""),
                price=float(item.get("price", 0)),
                price_formatted=f"{item.get('price', 0):,.0f} €".replace(",", " "),
                rooms=int(item.get("rooms", 0)),
                size=float(item.get("size", 0)),
                floor=item.get("floor", "N/A"),
                description=item.get("description", ""),
                thumbnail=item.get("thumbnail", ""),
                address=item.get("address", ""),
                municipality=item.get("municipality", ""),
                province=item.get("province", ""),
                operation=item.get("operation", ""),
                property_type=item.get("propertyType", ""),
            )
            properties.append(prop)

        return properties


def get_location_id(country: str, query: str) -> list[dict]:
    """
    Search for location IDs (requires API access).

    Note: This endpoint may not be available in all API tiers.
    Location IDs can also be found by inspecting Idealista URLs.
    """
    # Common Portugal location IDs for reference:
    PORTUGAL_LOCATIONS = {
        "lisboa": "0-EU-PT-11",
        "porto": "0-EU-PT-13",
        "funchal": "0-EU-PT-31-03",
        "madeira": "0-EU-PT-31",
        "camara-de-lobos": "0-EU-PT-31-02",
    }

    query_lower = query.lower()
    matches = []
    for name, loc_id in PORTUGAL_LOCATIONS.items():
        if query_lower in name:
            matches.append({"name": name, "locationId": loc_id})

    return matches
