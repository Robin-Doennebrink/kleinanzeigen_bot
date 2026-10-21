import json
import logging
import os
import platform
import re
import sys
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application, CallbackContext

from offerdict import OfferDict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv(dotenv_path="environment.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
if TELEGRAM_TOKEN is None or CHAT_ID is None:
    logger.error("Telegram Token or Chat ID not set => Abort start")
    sys.exit(1)

try:
    SEARCH_QUERIES = json.loads(os.getenv("SEARCH_QUERIES", "[]"))
except json.JSONDecodeError:
    logger.error("SEARCH_QUERIES could not be decoded => Abort start")
    sys.exit(1)

logger.info("(Try to) start kleinanzeigen bot")
logger.info(
    f"Loaded environment variables: TELEGRAM_TOKEN={TELEGRAM_TOKEN}, CHAT_ID={CHAT_ID}, SEARCH_QUERIES={SEARCH_QUERIES}"
)


# Define lock file path depending on the operating system
if platform.system() == "Windows":
    lock_file = os.path.join(os.getenv("TEMP", "C:\\temp"), "bot.lock")
else:
    lock_file = "/tmp/bot.lock"

# Check if another instance of the bot is already running
if os.path.exists(lock_file):
    logger.error(f"An instance of the bot is already running at {lock_file=}")
    sys.exit()

# Create the lock file
open(lock_file, "w").close()

bot = Bot(token=TELEGRAM_TOKEN)
sent_offers = []


def get_new_offers() -> dict[str, list[OfferDict]]:
    """
    Get all new offers for the specified search queries.

    Returns:
        A dictionary where each key is a search query URL and the corresponding value is a list of offer dictionaries.
        Each offer dictionary has the following keys:
            - 'title' (str): Title of the offer.
            - 'link' (str): Full URL link to the offer.
            - 'img_url' (str or None): URL of the offer's image, if available.
            - 'distance' (str): Distance or location information for the offer.
            - 'price' (str): Price of the item in the offer.
    """
    offers: dict[str, list[OfferDict]] = defaultdict(list)
    for query in SEARCH_QUERIES:
        logger.info(f"Query: {query=}")
        response = requests.get(query)
        soup = BeautifulSoup(response.text, "html.parser")
        for item in soup.select("article[data-adid][data-href]"):
            # Title
            title_element = item.select_one("h3 a")
            if title_element is None:
                logger.info("No title found, skipping element.")
                continue
            title = title_element.get_text(strip=True)
            # Link
            href = item.get("data-href")
            if not href:
                logger.info("No link found, skipping element.")
                continue
            logger.info(f"Found {href=}")
            link = "https://www.kleinanzeigen.de" + href

            # Location / distance
            location_element = item.select_one('svg[data-title="locationOutline"]')
            if location_element:
                location_container = location_element.parent
                distance = location_container.get_text(" ", strip=True)
                distance = re.sub(r"\s+", " ", distance)
            else:
                distance = "Distance not available"

            # Price
            price_element = item.select_one("p.text-title3.font-strong.text-secondary")
            if price_element:
                price = price_element.get_text(strip=True)
            else:
                price = "Price not available"

            # Image
            img_tag = item.select_one("[data-image-container] img")
            img_url: str | None = img_tag.get("src") if img_tag else None

            offers[query].append(
                {
                    "title": title,
                    "link": link,
                    "img_url": img_url,
                    "distance": distance,
                    "price": price,
                }
            )
    logger.info(f"Found in total {len(offers)} offers")
    return offers


async def send_offer(offer: OfferDict) -> None:
    """Sends the offer to the telegram chat.

    If image URL is available, it is sent as a photo, otherwise as a text message.
    Args:
        offer: Offer to send

    Returns: None

    """
    img_url = offer.get("img_url")
    text = f"{offer['title']}\n{offer['distance']}\n{offer['price']}\n{offer['link']}"

    # Send the image only if a valid image URL is available
    if img_url and img_url.startswith("http"):
        await bot.send_photo(chat_id=CHAT_ID, photo=img_url, caption=text)
    else:
        await bot.send_message(chat_id=CHAT_ID, text=text)


async def check_for_new_offers(context: CallbackContext) -> None:
    """Checks for Kleinanzeigen offers and sends them to the chat if they haven't been sent yet.

    Args:
        context: Application callback context

    Returns: None

    """
    logger.info("Start checking for new offers")
    # Check for new offers
    for query, offers in get_new_offers().items():
        for offer in offers:
            if offer not in sent_offers:
                await send_offer(offer)
                sent_offers.append(offer)


logger.info("Bot started with following queries:")
for query in SEARCH_QUERIES:
    logger.info(query)
# Create the Application object
app = Application.builder().token(TELEGRAM_TOKEN).build()
# Add a job that regularly checks for new offers
app.job_queue.run_repeating(check_for_new_offers, interval=5, first=0)

# Start bot
try:
    app.run_polling(drop_pending_updates=True)
finally:
    # Remove the lock file when the bot stops
    logger.debug("Bot terminated. Removing lock file")
    os.remove(lock_file)
