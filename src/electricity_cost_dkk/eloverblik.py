"""Client for eloverblik.dk's grid tariff data."""

from typing import Any

import requests

from .errors import UpstreamError, check_response

BASE_URL = "https://api.eloverblik.dk/customerapi/api"
REQUEST_TIMEOUT = 10
ELAFGIFT_PRICE_ID_PREFIX = "EA-"
ENERGINET_GLN = "5790000432752"
DEFAULT_HOURLY_POSITIONS = range(1, 25)


def get_access_token(refresh_token: str) -> str:
    response = requests.get(
        f"{BASE_URL}/token",
        headers={"Authorization": f"Bearer {refresh_token}"},
        timeout=REQUEST_TIMEOUT,
    )
    check_response(response, "eloverblik")
    return response.json()["result"]


def get_hourly_charges(access_token: str, metering_point_id: str) -> dict[str, dict[int, float]]:
    response = requests.post(
        f"{BASE_URL}/meteringpoints/meteringpoint/getcharges",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"meteringPoints": {"meteringPoint": [metering_point_id]}},
        timeout=REQUEST_TIMEOUT,
    )
    check_response(response, "eloverblik")
    payload: dict[str, Any] = response.json()
    results: list[dict[str, Any]] = payload.get("result") or []
    if not results:
        raise UpstreamError("eloverblik returned no result for this metering point")
    result = results[0]
    if not result.get("success", True):
        raise UpstreamError(result.get("errorText") or "eloverblik reported an unspecified error")
    tariffs: list[dict[str, Any]] = result["result"]["tariffs"]

    positions = sorted(
        {int(entry["position"]) for tariff in tariffs if tariff["periodType"] != "P1D" for entry in tariff["prices"]}
    ) or list(DEFAULT_HOURLY_POSITIONS)

    charges = {
        "distribution": dict.fromkeys(positions, 0.0),
        "transmission": dict.fromkeys(positions, 0.0),
        "tax": dict.fromkeys(positions, 0.0),
    }

    for tariff in tariffs:
        price_id = tariff.get("priceId") or ""
        name = (tariff.get("name") or "").lower()

        if price_id.startswith(ELAFGIFT_PRICE_ID_PREFIX) or "elafgift" in name:
            target = charges["tax"]
        elif tariff.get("owner") == ENERGINET_GLN:
            target = charges["transmission"]
        else:
            target = charges["distribution"]

        if tariff["periodType"] == "P1D":
            prices: list[dict[str, Any]] = tariff.get("prices") or []
            if not prices:
                continue
            flat_price = prices[0]["price"]
            for p in positions:
                target[p] += flat_price
        else:
            for entry in tariff["prices"]:
                target[int(entry["position"])] += entry["price"]

    return charges
