"""Electricity costs calculator for Denmark."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, NoReturn
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from . import __description__, __version__, eloverblik, nordpool
from .errors import UpstreamError

TIMEZONE = ZoneInfo("Europe/Copenhagen")
REGIONS = {"EAST": "DK2", "WEST": "DK1"}
NORDPOOL_HISTORY_DAYS = 62


def fail(message: str) -> NoReturn:
    print(json.dumps({"error": message}))
    sys.exit(1)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(json.dumps({"error": message}))
        sys.exit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = ArgumentParser(prog="electricity-cost-dkk", description=__description__)
    parser.add_argument("--config", metavar="PATH", help="load config from PATH")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "date",
        nargs="?",
        metavar="YYYY-MM-DD",
        help="optional date to fetch prices for (default: current date; last 62 days up to tomorrow)",
    )
    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def load_env(config_path: str | None) -> None:
    if config_path is not None:
        if not os.path.isfile(config_path):
            fail(f"Config file not found: {config_path}")
        try:
            load_dotenv(config_path)
        except OSError as e:
            fail(f"Could not read config file: {e}")
        return

    dotenv_path = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(dotenv_path):
        try:
            load_dotenv(dotenv_path)
        except OSError as e:
            fail(f"Could not read config file: {e}")


REQUIRED_VARS: list[tuple[str, Callable[[str], float | str]]] = [
    ("PROVIDER_MARKUP", float),
    ("VAT_RATE", float),
    ("ELOVERBLIK_TOKEN", str),
    ("ELOVERBLIK_METERING_POINT_ID", str),
]


def load_config() -> dict[str, Any]:
    zone = os.environ.get("REGION", "").strip().upper()
    if zone not in REGIONS:
        fail("REGION must be either EAST or WEST")

    values: dict[str, float | str] = {}
    for name, cast in REQUIRED_VARS:
        raw = os.environ.get(name, "").strip()
        if not raw:
            fail(f"{name} must be set")
        try:
            values[name] = cast(raw)
        except ValueError:
            fail(f"{name} must be set to a number")

    return {
        "zone": zone,
        "region": REGIONS[zone],
        "provider_markup": values["PROVIDER_MARKUP"],
        "vat_rate": values["VAT_RATE"],
        "refresh_token": values["ELOVERBLIK_TOKEN"],
        "metering_point_id": values["ELOVERBLIK_METERING_POINT_ID"],
    }


def fetch_spot_prices(region: str, date_str: str | None) -> tuple[list[float], str]:
    today = datetime.now(TIMEZONE).date()

    if date_str is not None:
        try:
            query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            fail(f"Invalid date '{date_str}', expected YYYY-MM-DD")

        max_date = today + timedelta(days=1)
        if query_date > max_date:
            fail(f"Cannot fetch prices for {query_date}.")

        min_date = today - timedelta(days=NORDPOOL_HISTORY_DAYS)
        if query_date < min_date:
            fail(
                f"Cannot fetch prices for {query_date}. Nord Pool only provides "
                f"data for the last {NORDPOOL_HISTORY_DAYS} days."
            )
    else:
        query_date = today

    try:
        hourly_spot = nordpool.get_hourly_spot_prices(region, query_date)
    except UpstreamError as e:
        fail(str(e))
    except Exception:
        fail("No price data available")

    if hourly_spot is None:
        fail("No price data available")

    return hourly_spot, str(query_date)


def main() -> None:
    args = parse_args(sys.argv[1:])

    load_env(args.config)
    config = load_config()
    hourly_spot, date_str = fetch_spot_prices(config["region"], args.date)

    try:
        access_token = eloverblik.get_access_token(config["refresh_token"])
    except UpstreamError as e:
        fail(str(e))
    except Exception:
        fail("Could not authenticate with eloverblik")

    try:
        charges = eloverblik.get_hourly_charges(access_token, config["metering_point_id"])
    except UpstreamError as e:
        fail(str(e))
    except Exception:
        fail("No grid tariff data available")

    prices: dict[str, Any] = {"date": date_str, "region": config["zone"], "currency": "DKK", "unit": "kWh", "hours": []}

    vat_rate = config["vat_rate"]

    def with_vat(amount: float) -> float:
        return amount * (1 + vat_rate)

    for hour in range(len(hourly_spot)):
        position = hour + 1
        try:
            spot_price_kwh = hourly_spot[hour] / 1000
            distribution_before_vat = charges["distribution"][position]
            transmission_before_vat = charges["transmission"][position]
            tax_before_vat = charges["tax"][position]
        except (IndexError, KeyError, TypeError):
            fail("No price data available")

        before_vat: dict[str, float] = {
            "spot": spot_price_kwh,
            "provider_markup": config["provider_markup"],
            "distribution": distribution_before_vat,
            "transmission": transmission_before_vat,
            "tax": tax_before_vat,
        }
        components = {name: round(with_vat(amount), 2) for name, amount in before_vat.items()}
        total = with_vat(sum(before_vat.values()))

        hour_data: dict[str, Any] = {
            "hour": hour,
            "components": components,
            "total": round(total, 2),
        }
        prices["hours"].append(hour_data)

    print(json.dumps(prices))
    sys.exit(0)
