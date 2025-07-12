"""Client for Nord Pool's spot prices."""

from datetime import date
from typing import Optional

import requests

from .errors import UpstreamError, check_response

API_URL = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPriceIndices"
REQUEST_TIMEOUT = 10


def get_hourly_spot_prices(area: str, target_date: date, currency: str = "DKK") -> Optional[list[float]]:
    response = requests.get(
        API_URL,
        params={
            "currency": currency,
            "market": "DayAhead",
            "date": target_date.strftime("%Y-%m-%d"),
            "resolutionInMinutes": 60,
            "indexNames": area,
        },
        timeout=REQUEST_TIMEOUT,
    )
    check_response(response, "Nord Pool")
    data = response.json()

    if data.get("currency") != currency:
        raise UpstreamError(f"Nord Pool returned prices in {data.get('currency')}, expected {currency}")

    entries = sorted(data.get("multiIndexEntries", []), key=lambda e: e["deliveryStart"])
    prices: list[float] = []
    for entry in entries:
        area_prices = entry.get("entryPerArea", {})
        if area not in area_prices:
            raise UpstreamError(f"Nord Pool response is missing a price for {area!r} at {entry.get('deliveryStart')}")
        prices.append(area_prices[area])

    return prices or None
