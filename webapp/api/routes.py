from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from webapp.database.database import get_db
from webapp.database.models import Listing
from webapp.api.schemas import (
    ListingCreate,
    ListingUpdate,
    ListingResponse,
    StageUpdate,
    ReorderRequest,
    UrlImportRequest,
    WebhookPayload,
)
from webapp.services.listing_service import ListingService
from webapp.services.scraper_service import ScraperService

router = APIRouter()


# =============================================================================
# Listings CRUD
# =============================================================================


@router.get("/listings")
async def get_all_listings(db: Session = Depends(get_db)):
    """Get all listings grouped by stage."""
    service = ListingService(db)
    grouped = service.get_all_grouped_by_stage()
    return {stage: [l.to_dict() for l in listings] for stage, listings in grouped.items()}


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Get a single listing by ID."""
    service = ListingService(db)
    listing = service.get_by_id(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("/listings", response_model=ListingResponse)
async def create_listing(data: ListingCreate, db: Session = Depends(get_db)):
    """Create a new listing manually."""
    service = ListingService(db)

    # Check for duplicate URL if provided
    if data.idealista_url:
        existing = service.get_by_url(data.idealista_url)
        if existing:
            raise HTTPException(status_code=400, detail="Listing with this URL already exists")

    listing = service.create(data)
    return listing


@router.put("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: int,
    data: ListingUpdate,
    db: Session = Depends(get_db)
):
    """Update a listing."""
    service = ListingService(db)
    listing = service.update(listing_id, data)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.delete("/listings/{listing_id}")
async def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    """Delete a listing."""
    service = ListingService(db)
    success = service.delete(listing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"status": "deleted", "id": listing_id}


# =============================================================================
# Stage and Position Updates (Drag-Drop)
# =============================================================================


@router.patch("/listings/{listing_id}/stage", response_model=ListingResponse)
async def update_stage(
    listing_id: int,
    data: StageUpdate,
    db: Session = Depends(get_db)
):
    """Move listing to a different stage (drag-drop action)."""
    service = ListingService(db)
    try:
        listing = service.update_stage(listing_id, data)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        return listing
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/listings/reorder/{stage}")
async def reorder_column(
    stage: str,
    data: ReorderRequest,
    db: Session = Depends(get_db)
):
    """Reorder cards within a column."""
    service = ListingService(db)
    service.reorder_column(stage, data.card_ids)
    return {"status": "reordered", "stage": stage}


# =============================================================================
# Import and Webhook
# =============================================================================


@router.post("/listings/import-url", response_model=ListingResponse)
async def import_from_url(data: UrlImportRequest, db: Session = Depends(get_db)):
    """Parse an Idealista URL and create a new listing."""
    service = ListingService(db)

    # Check for duplicate
    existing = service.get_by_url(data.url)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Listing already exists with ID {existing.id}"
        )

    try:
        # Parse the URL
        parsed = await ScraperService.parse_url(data.url)
        # Create listing
        listing_data = ListingCreate(**parsed, source="url_import")
        listing = service.create(listing_data)
        return listing
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse URL: {str(e)}")


@router.post("/webhook/telegram")
async def telegram_webhook(data: WebhookPayload, db: Session = Depends(get_db)):
    """Receive listings from Telegram bot."""
    service = ListingService(db)

    # Check for duplicate by URL
    if data.idealista_url:
        existing = service.get_by_url(data.idealista_url)
        if existing:
            return {"status": "duplicate", "id": existing.id}

    # Create new listing
    listing_data = ListingCreate(**data.model_dump())
    listing = service.create(listing_data)
    return {"status": "created", "id": listing.id}
