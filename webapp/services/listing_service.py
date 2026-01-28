from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from webapp.database.models import Listing
from webapp.api.schemas import ListingCreate, ListingUpdate, StageUpdate
from webapp.config import STAGE_VALUES


class ListingService:
    """Service for managing listings."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_grouped_by_stage(self) -> dict[str, list[Listing]]:
        """Get all listings grouped by stage, sorted by priority (highest first)."""
        listings = self.db.query(Listing).order_by(
            Listing.priority.desc(),
            Listing.position
        ).all()
        result = {stage: [] for stage in STAGE_VALUES}
        for listing in listings:
            if listing.stage in result:
                result[listing.stage].append(listing)
        return result

    def get_by_id(self, listing_id: int) -> Optional[Listing]:
        """Get a single listing by ID."""
        return self.db.query(Listing).filter(Listing.id == listing_id).first()

    def get_by_url(self, url: str) -> Optional[Listing]:
        """Get a listing by its Idealista URL."""
        return self.db.query(Listing).filter(Listing.idealista_url == url).first()

    def create(self, data: ListingCreate) -> Listing:
        """Create a new listing."""
        # Get next position for the stage
        max_pos = self.db.query(func.max(Listing.position)).filter(
            Listing.stage == data.stage
        ).scalar() or 0

        listing = Listing(
            **data.model_dump(),
            position=max_pos + 1
        )
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def update(self, listing_id: int, data: ListingUpdate) -> Optional[Listing]:
        """Update a listing."""
        listing = self.get_by_id(listing_id)
        if not listing:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(listing, field, value)

        self.db.commit()
        self.db.refresh(listing)
        return listing

    def update_stage(self, listing_id: int, data: StageUpdate) -> Optional[Listing]:
        """Move listing to a different stage."""
        listing = self.get_by_id(listing_id)
        if not listing:
            return None

        if data.stage not in STAGE_VALUES:
            raise ValueError(f"Invalid stage: {data.stage}")

        listing.stage = data.stage
        listing.position = data.position

        self.db.commit()
        self.db.refresh(listing)
        return listing

    def reorder_column(self, stage: str, card_ids: list[int]) -> bool:
        """Reorder cards within a column."""
        for position, card_id in enumerate(card_ids):
            listing = self.get_by_id(card_id)
            if listing and listing.stage == stage:
                listing.position = position
        self.db.commit()
        return True

    def delete(self, listing_id: int) -> bool:
        """Soft-delete a listing by moving it to the deleted stage."""
        listing = self.get_by_id(listing_id)
        if not listing:
            return False

        max_pos = self.db.query(func.max(Listing.position)).filter(
            Listing.stage == "deleted"
        ).scalar() or 0

        listing.stage = "deleted"
        listing.position = max_pos + 1
        self.db.commit()
        return True
