#!/usr/bin/env python3
"""Simple Telegram bot that periodically checks for new Idealista listings."""

import asyncio
import logging
import random
import re
from typing import Callable, Iterable
from telegram import Bot

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    IDEALISTA_URL,
    SCRAPE_INTERVAL_MIN,
    SCRAPE_INTERVAL_MAX,
)
from idealista.scraper import scrape_all_pages, load_seen_listings, Listing
from watchlist import add_watch_url, load_watch_urls

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


def save_listing_to_db(listing: Listing) -> bool:
    """Save a listing to the web CRM database."""
    if not DB_AVAILABLE:
        return False

    try:
        db = SessionLocal()
        # Check if already exists
        existing = db.query(DBListing).filter(
            DBListing.idealista_url == listing.url
        ).first()

        if existing:
            db.close()
            return False

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
            stage="to_be_communicated",
            source="telegram",
        )
        db.add(db_listing)
        db.commit()
        db.close()
        logger.info(f"Saved listing to CRM: {listing.title}")
        return True
    except Exception as e:
        logger.error(f"Failed to save listing to DB: {e}")
        return False


def _extract_idealista_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = []
    for match in IDEALISTA_URL_RE.finditer(text):
        url = match.group(0).rstrip(TRAILING_PUNCTUATION)
        if url:
            urls.append(url)
    return urls


def _get_watch_urls(urls: Iterable[str]) -> list[str]:
    return sorted(set(urls))


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


async def send_listings(
    bot: Bot,
    listings: list[Listing],
    chat_id: str | int = TELEGRAM_CHAT_ID,
) -> None:
    """Send listings to Telegram."""
    for listing in listings:
        try:
            message = format_message(listing)

            # Try with photo first
            if listing.thumbnail and listing.thumbnail.startswith("http"):
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=listing.thumbnail,
                        caption=message,
                        parse_mode="Markdown"
                    )
                except Exception:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown"
                    )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown"
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
        logger.info(f"Found {len(listings)} new listings, sending...")
        # Save to web CRM database
        for listing in listings:
            save_listing_to_db(listing)
        await send_listings(bot, listings, chat_id=chat_id)
    else:
        logger.info("No new listings")


async def run_scraper_loop(
    bot: Bot,
    stop_event: asyncio.Event,
    get_urls: Callable[[], list[str]],
    chat_id: str | int = TELEGRAM_CHAT_ID,
    lock: asyncio.Lock | None = None,
) -> None:
    """Run periodic scraping until stop_event is set."""
    load_seen_listings()

    while not stop_event.is_set():
        try:
            # urls = get_urls()
            urls = []
        except Exception as exc:
            logger.error(f"Failed to load watch URLs: {exc}")
            urls = []

        for url in urls:
            try:
                if lock:
                    async with lock:
                        await check_and_notify(bot, base_url=url, chat_id=chat_id)
                else:
                    await check_and_notify(bot, base_url=url, chat_id=chat_id)
            except Exception as exc:
                logger.error(f"Error checking URL {url}: {exc}")

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


async def _handle_message(bot: Bot, message, watch_urls: set[str], lock: asyncio.Lock) -> None:
    if not message or not message.text:
        return

    logger.info(f"Received message: {message.text}")
    # chat_id = message.chat_id
    # urls = _extract_idealista_urls(message.text)
    # if not urls:
    #     await bot.send_message(
    #         chat_id=chat_id,
    #         text="Send me an Idealista link to track.",
    #     )
    #     return

    # for url in urls:
    #     added = add_watch_url(watch_urls, url)
    #     if added:
    #         await bot.send_message(chat_id=chat_id, text=f"Added to watch list:\n{url}")
    #     else:
    #         await bot.send_message(chat_id=chat_id, text=f"Already watching:\n{url}")

    #     asyncio.create_task(_scrape_now(bot, url, chat_id, lock))


async def run_polling(
    bot: Bot,
    stop_event: asyncio.Event,
    watch_urls: set[str],
    lock: asyncio.Lock,
) -> None:
    offset = None
    while not stop_event.is_set():
        try:
            updates = await bot.get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update.update_id + 1
                message = update.message or update.edited_message
                await _handle_message(bot, message, watch_urls, lock)
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
    watch_urls = load_watch_urls()
    scrape_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    logger.info(
        f"Bot started! Checking every {SCRAPE_INTERVAL_MIN}-{SCRAPE_INTERVAL_MAX} seconds"
    )
    logger.info(f"Search URL: {IDEALISTA_URL}")

    polling_task = asyncio.create_task(run_polling(bot, stop_event, watch_urls, scrape_lock))

    if TELEGRAM_CHAT_ID:
        scraper_task = asyncio.create_task(
            run_scraper_loop(
                bot,
                stop_event,
                lambda: _get_watch_urls(watch_urls),
                chat_id=TELEGRAM_CHAT_ID,
                lock=scrape_lock,
            )
        )
        await asyncio.gather(polling_task, scraper_task)
    else:
        await polling_task


if __name__ == "__main__":
    asyncio.run(main())
