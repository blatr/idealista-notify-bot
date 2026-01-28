#!/usr/bin/env python3
"""Simple Telegram bot that periodically checks for new Idealista listings."""

from __future__ import annotations

import asyncio
import logging
import random
import re
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    IDEALISTA_URL,
    SCRAPE_INTERVAL_MIN,
    SCRAPE_INTERVAL_MAX,
)
from idealista.scraper import (
    scrape_all_pages,
    Listing,
)
from webapp.services.scraper_service import parse_idealista_url

# Database integration for web CRM
try:
    from webapp.database.database import SessionLocal
    from webapp.database.models import Listing as DBListing
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

IDEALISTA_URL_RE = re.compile(r"https?://(?:www\.)?idealista\.[^\s]+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,)>]"
STAGE_PRELIMINARY = "preliminary"
STAGE_TO_BE_COMMUNICATED = "to_be_communicated"
CALLBACK_PREFIX = "promote"


def save_listing_to_db(listing: Listing) -> DBListing | None:
    """Save a listing to the web CRM database."""
    if not DB_AVAILABLE:
        return None

    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(DBListing).filter(
            DBListing.idealista_url == listing.url
        ).first()

        if existing:
            return existing

        max_pos = db.query(func.max(DBListing.position)).filter(
            DBListing.stage == STAGE_PRELIMINARY
        ).scalar() or 0

        # Create new listing
        db_listing = DBListing(
            idealista_url=listing.url,
            title=listing.title,
            price=listing.price,
            price_value=listing.price_value,
            rooms=listing.rooms,
            size=listing.size,
            floor=listing.floor,
            description=listing.description,
            thumbnail=listing.thumbnail,
            stage=STAGE_PRELIMINARY,
            position=max_pos + 1,
            source="telegram",
        )
        db.add(db_listing)
        db.commit()
        db.refresh(db_listing)
        logger.info(f"Saved listing to CRM: {listing.title}")
        return db_listing
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save listing to DB: {e}")
        return None
    finally:
        db.close()


def update_listing_stage(listing_id: int, new_stage: str) -> str:
    """Update a listing stage and position."""
    if not DB_AVAILABLE:
        return "db_unavailable"

    db = SessionLocal()
    try:
        listing = db.query(DBListing).filter(DBListing.id == listing_id).first()
        if not listing:
            return "not_found"

        if listing.stage == new_stage:
            return "already"

        max_pos = db.query(func.max(DBListing.position)).filter(
            DBListing.stage == new_stage
        ).scalar() or 0

        listing.stage = new_stage
        listing.position = max_pos + 1
        db.commit()
        return "updated"
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update listing stage: {e}")
        return "error"
    finally:
        db.close()


def filter_new_listings(listings: list[Listing]) -> list[Listing]:
    """Filter out listings already present in the DB."""
    if not DB_AVAILABLE or not listings:
        return listings

    urls = [listing.url for listing in listings if listing.url]
    if not urls:
        return listings

    db = SessionLocal()
    try:
        existing = db.query(DBListing.idealista_url).filter(
            DBListing.idealista_url.in_(urls)
        ).all()
        existing_urls = {row[0] for row in existing}
    finally:
        db.close()

    return [listing for listing in listings if listing.url not in existing_urls]


async def create_listing_from_url(url: str) -> tuple[str, DBListing | None]:
    """Scrape a single listing URL and create/promote it in the CRM."""
    if not DB_AVAILABLE:
        return "db_unavailable", None

    try:
        listing_data = await parse_idealista_url(url)
    except Exception as exc:
        logger.error(f"Failed to parse listing URL {url}: {exc}")
        return "scrape_failed", None

    db = SessionLocal()
    try:
        existing = db.query(DBListing).filter(DBListing.idealista_url == url).first()
        max_pos = db.query(func.max(DBListing.position)).filter(
            DBListing.stage == STAGE_TO_BE_COMMUNICATED
        ).scalar() or 0

        if existing:
            if existing.stage != STAGE_TO_BE_COMMUNICATED:
                existing.stage = STAGE_TO_BE_COMMUNICATED
                existing.position = max_pos + 1
                db.commit()
                return "promoted", existing
            return "exists", existing

        listing = DBListing(
            title=listing_data.get("title"),
            price=listing_data.get("price"),
            price_value=listing_data.get("price_value"),
            rooms=listing_data.get("rooms"),
            size=listing_data.get("size"),
            floor=listing_data.get("floor"),
            description=listing_data.get("description"),
            thumbnail=listing_data.get("thumbnail"),
            idealista_url=listing_data.get("idealista_url") or url,
            stage=STAGE_TO_BE_COMMUNICATED,
            position=max_pos + 1,
            source="telegram",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return "created", listing
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save listing from URL: {exc}")
        return "error", None
    finally:
        db.close()


def _extract_idealista_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = []
    for match in IDEALISTA_URL_RE.finditer(text):
        url = match.group(0).rstrip(TRAILING_PUNCTUATION)
        if url:
            urls.append(url)
    return urls


def format_message(listing: Listing) -> str:
    """Format a listing for Telegram."""
    return (
        f"🏠 *{listing.title}*\n\n"
        f"💰 *{listing.price}*\n"
        f"🛏 {listing.rooms}\n"
        f"📐 {listing.size}\n"
        f"🏢 {listing.floor}\n\n"
        f"[Ver anuncio]({listing.url})"
    )


def build_listing_markup(db_listing: DBListing | None) -> InlineKeyboardMarkup | None:
    """Build inline keyboard for a listing message."""
    if not db_listing or db_listing.stage != STAGE_PRELIMINARY:
        return None

    callback_data = f"{CALLBACK_PREFIX}:{db_listing.id}"
    keyboard = [
        [InlineKeyboardButton("❤️ Like", callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_listings(
    bot: Bot,
    listings: list[tuple[Listing, DBListing | None]],
    chat_id: str | int = TELEGRAM_CHAT_ID,
) -> None:
    """Send listings to Telegram."""
    for listing, db_listing in listings:
        try:
            message = format_message(listing)
            reply_markup = build_listing_markup(db_listing)

            # Try with photo first
            if listing.thumbnail and listing.thumbnail.startswith("http"):
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=listing.thumbnail,
                        caption=message,
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                    )
                except Exception:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                    )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )

            await asyncio.sleep(1)  # Don't spam

        except Exception as e:
            logger.error(f"Error sending message: {e}")


async def check_and_notify(
    bot: Bot,
    base_url: str | None = None,
    chat_id: str | int = TELEGRAM_CHAT_ID,
) -> None:
    """Check for new listings and send notifications."""
    logger.info("Checking for new listings...")

    listings, error = scrape_all_pages(base_url)

    if error:
        logger.error("Scraping failed")
        return

    if listings:
        listings = filter_new_listings(listings)
        if not listings:
            logger.info("No new listings (all already in DB)")
            return

        logger.info(f"Found {len(listings)} new listings, sending...")
        # Save to web CRM database
        saved = []
        for listing in listings:
            db_listing = save_listing_to_db(listing)
            saved.append((listing, db_listing))
        await send_listings(bot, saved, chat_id=chat_id)
    else:
        logger.info("No new listings")


async def run_scraper_loop(
    bot: Bot,
    stop_event: asyncio.Event,
    base_url: str | None = None,
    chat_id: str | int = TELEGRAM_CHAT_ID,
    lock: asyncio.Lock | None = None,
) -> None:
    """Run periodic scraping until stop_event is set."""
    while not stop_event.is_set():
        try:
            if lock:
                async with lock:
                    await check_and_notify(bot, base_url=base_url, chat_id=chat_id)
            else:
                await check_and_notify(bot, base_url=base_url, chat_id=chat_id)
        except Exception as exc:
            logger.error(f"Error checking URL {base_url}: {exc}")

        delay = (
            SCRAPE_INTERVAL_MIN
            if SCRAPE_INTERVAL_MAX <= SCRAPE_INTERVAL_MIN
            else random.randint(SCRAPE_INTERVAL_MIN, SCRAPE_INTERVAL_MAX)
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            continue


async def _scrape_now(
    bot: Bot,
    target_url: str,
    target_chat: int,
    lock: asyncio.Lock,
) -> None:
    async with lock:
        await check_and_notify(
            bot,
            base_url=target_url,
            chat_id=target_chat,
        )


async def _handle_message(bot: Bot, message, lock: asyncio.Lock = None) -> None:
    if not message or not message.text:
        return

    logger.info(f"Received message: {message.text}")
    chat_id = message.chat_id
    urls = _extract_idealista_urls(message.text)
    if not urls:
        return

    for url in sorted(set(urls)):
        try:
            if lock:
                async with lock:
                    status, listing = await create_listing_from_url(url)
            else:
                status, listing = await create_listing_from_url(url)
        except Exception as exc:
            logger.error(f"Failed handling URL {url}: {exc}")
            await bot.send_message(chat_id=chat_id, text=f"Failed to import:\n{url}")
            continue

        if status == "created":
            title = listing.title if listing else "Listing"
            await bot.send_message(chat_id=chat_id, text=f"Added to CRM:\n{title}")
        elif status == "promoted":
            await bot.send_message(chat_id=chat_id, text="Moved to To Be Communicated.")
        elif status == "exists":
            await bot.send_message(chat_id=chat_id, text="Listing already exists.")
        elif status == "db_unavailable":
            await bot.send_message(chat_id=chat_id, text="Database not available.")
        elif status == "scrape_failed":
            await bot.send_message(chat_id=chat_id, text="Failed to parse listing URL.")
        else:
            await bot.send_message(chat_id=chat_id, text="Failed to save listing.")


async def _handle_callback(bot: Bot, callback_query, lock: asyncio.Lock = None) -> None:
    if not callback_query or not callback_query.data:
        return

    data = callback_query.data
    if not data.startswith(f"{CALLBACK_PREFIX}:"):
        return

    listing_id_raw = data.split(":", 1)[1]
    if not listing_id_raw.isdigit():
        await callback_query.answer("Invalid action.")
        return

    listing_id = int(listing_id_raw)
    if lock:
        async with lock:
            result = update_listing_stage(listing_id, STAGE_TO_BE_COMMUNICATED)
    else:
        result = update_listing_stage(listing_id, STAGE_TO_BE_COMMUNICATED)

    if result == "updated":
        await callback_query.answer("Moved to To Be Communicated.")
        if callback_query.message:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=callback_query.message.chat_id,
                    message_id=callback_query.message.message_id,
                    reply_markup=None,
                )
            except Exception as exc:
                logger.error(f"Failed to clear reply markup: {exc}")
    elif result == "already":
        await callback_query.answer("Already marked.")
    elif result == "not_found":
        await callback_query.answer("Listing not found.")
    elif result == "db_unavailable":
        await callback_query.answer("Database not available.")
    else:
        await callback_query.answer("Failed to update listing.")


async def run_polling(
    bot: Bot,
    stop_event: asyncio.Event,
    lock: asyncio.Lock,
) -> None:
    offset = None
    while not stop_event.is_set():
        try:
            updates = await bot.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update.update_id + 1
                if update.callback_query:
                    await _handle_callback(bot, update.callback_query, lock)
                    continue
                message = update.message or update.edited_message
                await _handle_message(bot, message, lock)
        except Exception as exc:
            logger.error(f"Polling error: {exc}")
            await asyncio.sleep(2)


async def main():
    """Main loop."""
    # Validate config
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    scrape_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    logger.info(
        f"Bot started! Checking every {SCRAPE_INTERVAL_MIN}-{SCRAPE_INTERVAL_MAX} seconds"
    )
    logger.info(f"Search URL: {IDEALISTA_URL}")

    polling_task = asyncio.create_task(run_polling(bot, stop_event, scrape_lock))

    if TELEGRAM_CHAT_ID:
        scraper_task = asyncio.create_task(
            run_scraper_loop(
                bot,
                stop_event,
                base_url=IDEALISTA_URL,
                chat_id=TELEGRAM_CHAT_ID,
                lock=scrape_lock,
            )
        )
        await asyncio.gather(polling_task, scraper_task)
    else:
        await polling_task


if __name__ == "__main__":
    asyncio.run(main())
