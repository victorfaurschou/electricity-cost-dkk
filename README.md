# electricity-cost-dkk

Combines spot prices, grid tariffs, and provider markup to calculate the total hourly electricity cost for a given day, including all applicable fees and taxes.

## Usage

### Install

```sh
pip install electricity-cost-dkk
```

Alternatively, install from source:

```sh
git clone https://github.com/victorfaurschou/electricity-cost-dkk.git
cd electricity-cost-dkk
poetry install
```

### Configure

Set the following:

```
REGION=
ELOVERBLIK_METERING_POINT_ID=
ELOVERBLIK_TOKEN=
PROVIDER_MARKUP=
VAT_RATE=0.25
```

1. Set your region as either `EAST` (Sjælland, Lolland-Falster, Møn and Bornholm) or `WEST` (Jylland and Fyn)
2. Set your metering point identifier and access token from: [eloverblik.dk](https://eloverblik.dk)
3. Set your provider's markup (usually be found on your billing statement)

You can provide them in any of these ways:

- Export them in your environment.
- Place a `.env` file in the directory you run the program from (if installed from source, copy `.env.example` as a starting point).
- Pass `--config PATH` to load them from a specific file instead.

### Run

```sh
electricity-cost-dkk
```

Alternatively, if installed from source:

```sh
poetry run electricity-cost-dkk
```

By default, the tool fetches today's prices. To fetch prices for a different date, provide a YYYY-MM-DD date instead - any date from the last 62 days up to tomorrow's.

#### Output

A JSON object with one entry per hour of the day, each showing a breakdown of cost components (spot price, provider markup, distribution fee, transmission fee, and tax) plus the total cost.

Example:

```json
{
  "date": "2026-01-24",
  "region": "EAST",
  "currency": "DKK",
  "unit": "kWh",
  "hours": [
    {
      "hour": 0,
      "components": {
        "spot": 1.01,
        "provider_markup": 0.19,
        "distribution": 0.13,
        "transmission": 0.14,
        "tax": 0.01
      },
      "total": 1.48
    },
    {
      "hour": 17,
      "components": {
        "spot": 1.45,
        "provider_markup": 0.19,
        "distribution": 0.52,
        "transmission": 0.14,
        "tax": 0.01
      },
      "total": 2.31
    }
  ]
}
```

## Availability

Today's prices are always available, as Nord Pool publishes each day's prices one day in advance. Tomorrow's prices become available once Nord Pool publishes them, typically around 13:00. Requests made before then will return no data. Nord Pool doesn't publish further ahead than that.

This day-ahead price data also isn't retained indefinitely - only the past 62 days are available, and requesting an older date will fail.

## Scope

This tool is primarily a data source rather than an end-user utility. It's intended to be piped into or consumed by other tools, so it doesn't provide a human-friendly output format.

While Nord Pool operates in other countries besides Denmark, this tool assumes Danish structures and won't work directly for other countries.

## Limitations

Grid tariffs (distribution, transmission, tax) always reflect today's currently active rate, even when you request a past or future date - eloverblik has no historical tariff data. If your grid company's rates have changed since the requested date, those components won't match what was actually billed that day; only the spot price will be historically accurate.

## Notes

Testing was done with [OK a.m.b.a.](https://www.ok.dk/) as the provider and [Radius Elnet](https://radiuselnet.dk/) as the grid company.

### Price discrepancy

If totals deviate from what you see on your provider's mobile app, website, or billing statement, it may be because they use a different data source, calculation method or fee structure.