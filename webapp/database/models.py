from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func

from webapp.database.database import Base


class Listing(Base):
    """Apartment listing model for the Kanban board."""

    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    idealista_url = Column(String, unique=True, index=True, nullable=True)

    # Listing details (matching existing scraper dataclass)
    title = Column(String, nullable=False)
    price = Column(String)
    price_value = Column(Float, default=0)
    rooms = Column(String)
    size = Column(String)
    floor = Column(String)
    description = Column(Text)
    thumbnail = Column(String)

    # CRM fields
    stage = Column(String, default="to_be_communicated", index=True)
    notes = Column(Text)
    position = Column(Integer, default=0)
    priority = Column(Integer, default=0)  # 0-10, higher = more important
    source = Column(String, default="manual")  # 'manual', 'telegram', 'scraper', 'url_import'

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "idealista_url": self.idealista_url,
            "title": self.title,
            "price": self.price,
            "price_value": self.price_value,
            "rooms": self.rooms,
            "size": self.size,
            "floor": self.floor,
            "description": self.description,
            "thumbnail": self.thumbnail,
            "stage": self.stage,
            "notes": self.notes,
            "position": self.position,
            "priority": self.priority,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
