"""
Description: A dictionary which describes a Kleinanzeigen offer.

Author: Robin
Created: 29.10.2025
Copyright: © 2025 Robin Dönnebrink
"""
from typing import TypedDict


class OfferDict(TypedDict):
    title: str
    link: str
    img_url: str | None
    distance: str
    price: str