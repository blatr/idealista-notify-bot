import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/listings.db")

# Reuse existing Scrapfly key from parent config
SCRAPFLY_API_KEY = os.getenv("SCRAPFLY_API_KEY", "scp-live-1e9e5558c13049ccab83bc04ff5dab0f")

# Web app settings
HOST = os.getenv("WEB_HOST", "0.0.0.0")
PORT = int(os.getenv("WEB_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Kanban stages configuration (UI-visible stages only)
STAGES = [
    {"value": "to_be_communicated", "label": "To Be Communicated", "color": "blue"},
    {"value": "message_sent", "label": "Message Sent", "color": "yellow"},
    {"value": "called_by_phone", "label": "Called by Phone", "color": "purple"},
    {"value": "in_progress", "label": "In Progress", "color": "orange"},
    {"value": "agreed_on_viewing", "label": "Agreed on Viewing", "color": "green"},
    {"value": "waiting_reply", "label": "Waiting Reply", "color": "amber"},
    {"value": "rejected", "label": "Rejected", "color": "red"},
]

# Stages allowed in data layer (includes internal-only stages)
INTERNAL_STAGES = ["preliminary", "deleted"]

STAGE_VALUES = [s["value"] for s in STAGES] + INTERNAL_STAGES
