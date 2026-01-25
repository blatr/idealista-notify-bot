#!/usr/bin/env python3
"""Simple Telegram bot that periodically checks for new Idealista listings."""

import asyncio
import logging
import random
from telegram import Bot

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    IDEALISTA_URL,
    SCRAPE_INTERVAL_MIN,
    SCRAPE_INTERVAL_MAX,
)
from idealista.scraper import scrape_all_pages, load_seen_listings, Listing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


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


async def send_listings(bot: Bot, listings: list[Listing]) -> None:
    """Send listings to Telegram."""
    for listing in listings:
        try:
            message = format_message(listing)

            # Try with photo first
            if listing.thumbnail and listing.thumbnail.startswith("http"):
                try:
                    await bot.send_photo(
                        chat_id=TELEGRAM_CHAT_ID,
                        photo=listing.thumbnail,
                        caption=message,
                        parse_mode="Markdown"
                    )
                except Exception:
                    await bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=message,
                        parse_mode="Markdown"
                    )
            else:
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=message,
                    parse_mode="Markdown"
                )

            await asyncio.sleep(1)  # Don't spam

        except Exception as e:
            logger.error(f"Error sending message: {e}")


async def check_and_notify(bot: Bot) -> None:
    """Check for new listings and send notifications."""
    logger.info("Checking for new listings...")

    listings, error = scrape_all_pages()

    if error:
        logger.error("Scraping failed")
        return

    if listings:
        logger.info(f"Found {len(listings)} new listings, sending...")
        await send_listings(bot, listings)
    else:
        logger.info("No new listings")


async def main():
    """Main loop."""
    # Validate config
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        return
    if not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_CHAT_ID not set in .env")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Load seen listings on start
    load_seen_listings()

    logger.info(
        f"Bot started! Checking every {SCRAPE_INTERVAL_MIN}-{SCRAPE_INTERVAL_MAX} seconds"
    )
    logger.info(f"Search URL: {IDEALISTA_URL}")

    # Send startup message
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=f"🤖 Bot started!\nChecking: {IDEALISTA_URL}"
    )

    # Main loop
    while True:
        try:
            await check_and_notify(bot)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        delay = (
            SCRAPE_INTERVAL_MIN
            if SCRAPE_INTERVAL_MAX <= SCRAPE_INTERVAL_MIN
            else random.randint(SCRAPE_INTERVAL_MIN, SCRAPE_INTERVAL_MAX)
        )
        await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
