import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Telegram Bot
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =============================================================================
# Scrapfly (for bypassing anti-bot protection)
# =============================================================================
SCRAPFLY_API_KEY = os.getenv("SCRAPFLY_API_KEY", "scp-live-1e9e5558c13049ccab83bc04ff5dab0f")

# =============================================================================
# Search Configuration
# =============================================================================

DEFAULT_IDEALISTA_URL = (
    "https://www.idealista.com/alquiler-viviendas/barcelona-barcelona/"
    "con-precio-hasta_2700,precio-desde_1000,alquiler-de-larga-temporada/"
    "?ordenado-por=fecha-publicacion-desc"
)

# Allow env override for quick changes without code edits.
IDEALISTA_URL = os.getenv("IDEALISTA_URL") or DEFAULT_IDEALISTA_URL

# =============================================================================
# Filtering
# =============================================================================
EXCLUDED_AREAS = []
EXCLUDED_TERMS = []
EXCLUDED_FLOORS = []

# =============================================================================
# Data Storage
# =============================================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SEEN_LISTINGS_FILE = os.path.join(DATA_DIR, "seen_links.txt")

# =============================================================================
# Scraping Settings
# =============================================================================
SCRAPE_INTERVAL_MIN = 600  # 10 minutes (be gentle with Scrapfly credits)
SCRAPE_INTERVAL_MAX = 780  # 13 minutes
