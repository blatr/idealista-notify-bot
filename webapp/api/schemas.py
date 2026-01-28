from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ListingBase(BaseModel):
    """Base schema for listing data."""

    title: str
    price: Optional[str] = None
    price_value: Optional[float] = 0
    rooms: Optional[str] = None
    size: Optional[str] = None
    floor: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    idealista_url: Optional[str] = None
    notes: Optional[str] = None


class ListingCreate(ListingBase):
    """Schema for creating a new listing."""

    stage: Optional[str] = "to_be_communicated"
    source: Optional[str] = "manual"


class ListingUpdate(BaseModel):
    """Schema for updating a listing."""

    title: Optional[str] = None
    price: Optional[str] = None
    price_value: Optional[float] = None
    rooms: Optional[str] = None
    size: Optional[str] = None
    floor: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    idealista_url: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = None


class ListingResponse(ListingBase):
    """Schema for listing response."""

    id: int
    stage: str
    position: int
    priority: int = 0
    source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StageUpdate(BaseModel):
    """Schema for updating listing stage (drag-drop)."""

    stage: str
    position: Optional[int] = 0


class ReorderRequest(BaseModel):
    """Schema for reordering cards within a column."""

    card_ids: list[int] = Field(..., description="Ordered list of card IDs")


class UrlImportRequest(BaseModel):
    """Schema for importing a listing from URL."""

    url: str


class WebhookPayload(BaseModel):
    """Schema for Telegram bot webhook."""

    title: str
    price: Optional[str] = None
    price_value: Optional[float] = 0
    rooms: Optional[str] = None
    size: Optional[str] = None
    floor: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    idealista_url: Optional[str] = None
    source: str = "telegram"
