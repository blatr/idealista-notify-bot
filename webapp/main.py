from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import os

from webapp.database.database import get_db, engine
from webapp.database import models
from webapp.api.routes import router as api_router
from webapp.services.listing_service import ListingService
from webapp.config import STAGES, HOST, PORT

# Create tables on startup
models.Base.metadata.create_all(bind=engine)

# Support subpath deployment (e.g., /crm)
ROOT_PATH = os.getenv("ROOT_PATH", "")

app = FastAPI(
    title="Apartment CRM",
    description="Trello-like CRM for managing apartment listings",
    root_path=ROOT_PATH
)

# Get the webapp directory path
WEBAPP_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(WEBAPP_DIR, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(WEBAPP_DIR, "templates"))

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def board(request: Request, db: Session = Depends(get_db)):
    """Render main Kanban board."""
    service = ListingService(db)
    columns = service.get_all_grouped_by_stage()

    return templates.TemplateResponse(
        "board.html",
        {
            "request": request,
            "stages": STAGES,
            "columns": columns,
            "base_url": ROOT_PATH,
        }
    )


@app.get("/partials/card/{listing_id}", response_class=HTMLResponse)
async def get_card_partial(listing_id: int, request: Request, db: Session = Depends(get_db)):
    """Get single card HTML partial (for htmx updates)."""
    service = ListingService(db)
    listing = service.get_by_id(listing_id)
    if not listing:
        return HTMLResponse(content="", status_code=404)

    return templates.TemplateResponse(
        "partials/card.html",
        {"request": request, "listing": listing, "base_url": ROOT_PATH}
    )


@app.get("/partials/card-detail/{listing_id}", response_class=HTMLResponse)
async def get_card_detail(listing_id: int, request: Request, db: Session = Depends(get_db)):
    """Get card detail modal content."""
    service = ListingService(db)
    listing = service.get_by_id(listing_id)
    if not listing:
        return HTMLResponse(content="<p>Listing not found</p>", status_code=404)

    return templates.TemplateResponse(
        "partials/card_detail.html",
        {"request": request, "listing": listing, "stages": STAGES, "base_url": ROOT_PATH}
    )


@app.get("/partials/card-form", response_class=HTMLResponse)
async def get_card_form(request: Request):
    """Get card creation form modal."""
    return templates.TemplateResponse(
        "partials/card_form.html",
        {"request": request, "stages": STAGES, "base_url": ROOT_PATH}
    )


@app.get("/partials/import-form", response_class=HTMLResponse)
async def get_import_form(request: Request):
    """Get URL import form modal."""
    return templates.TemplateResponse(
        "partials/import_form.html",
        {"request": request, "base_url": ROOT_PATH}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
