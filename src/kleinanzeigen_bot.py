from collections import defaultdict
from telegram import Bot
from telegram.ext import Application, CallbackContext
import requests
from bs4 import BeautifulSoup
import re
import os
import sys
import json
import platform
import logging
from dotenv import load_dotenv

from offerdict import OfferDict

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
logger.info(f"Loaded environment variables: TELEGRAM_TOKEN={TELEGRAM_TOKEN}, CHAT_ID={CHAT_ID}, SEARCH_QUERIES={SEARCH_QUERIES}")


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
open(lock_file, 'w').close()

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
        response = requests.get(query)
        soup = BeautifulSoup(response.text, 'html.parser')

        for item in soup.select('article.aditem'):
            # Check if the <h2> element exists
            title_element = item.select_one('h2')
            if title_element is None:
                logger.info("No title found, skipping element.")
                continue

            title = title_element.text.strip()
            link_element = item.select_one('a')
            if link_element is None or 'href' not in link_element.attrs:
                logger.info("No link found, skipping element.")
                continue
            link = "https://www.kleinanzeigen.de" + link_element['href']

            # Extract and clean the distance text
            distance_element = item.select_one('.aditem-main--top--left')
            if distance_element:
                distance = distance_element.text.strip()
                distance = re.sub(r'\s+', ' ', distance)
            else:
                distance = "Distance not available"

            price = item.select_one(".aditem-main--middle--price-shipping--price")
            if price:
                price = price.text.strip()
            else:
                price = "Price not available"

            # Check if an image is available
            img_tag = item.select_one('img')
            img_url: str | None = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None

            offers[query].append({
                'title': title,
                'link': link,
                'img_url': img_url,
                'distance': distance,
                "price": price
            })
    return offers


async def send_offer(offer: OfferDict) -> None:
    """Sends the offer to the telegram chat.

    If image URL is available, it is sent as a photo, otherwise as a text message.
    Args:
        offer: Offer to send

    Returns: None

    """
    img_url = offer.get('img_url')
    text = f"{offer['title']}\n{offer['distance']}\n{offer['price']}\n{offer['link']}"

    # Send the image only if a valid image URL is available
    if img_url and img_url.startswith("http"):
        await bot.send_photo(chat_id=CHAT_ID, photo=img_url, caption=text)
    else:
        await bot.send_message(chat_id=CHAT_ID, text=text)


async def check_for_new_offers(context:  CallbackContext) -> None:
    """ Checks for Kleinanzeigen offers and sends them to the chat if they haven't been sent yet.

    Args:
        context: Application callback context

    Returns: None

    """
    # Check for new offers
    for query, offers in get_new_offers().items():
        for offer in offers:
            if offer not in sent_offers:
                await send_offer(offer)
                sent_offers.append(offer)


# Create the Application object
app = Application.builder().token(TELEGRAM_TOKEN).build()
# Add a job that regularly checks for new offers
app.job_queue.run_repeating(check_for_new_offers, interval=5, first=0)

# Start bot
try:
    app.run_polling()
finally:
    # Remove the lock file when the bot stops
    logger.debug("Bot terminated. Removing lock file")
    os.remove(lock_file)
