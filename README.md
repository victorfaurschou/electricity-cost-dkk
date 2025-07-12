# electricity-cost-dkk

Combines spot prices, grid tariffs, and provider markup to calculate the total hourly electricity cost for a given day, including all applicable fees and taxes.

## Usage

### Install

```sh
poetry install
```

### Configure

1. Copy `.env.example` to `.env`
2. Set your region (`EAST` or `WEST` - Sjælland, Lolland-Falster, Møn and Bornholm is East; Jylland and Fyn is West)
3. Set your metering point ID and API token from [eloverblik.dk](https://eloverblik.dk)
4. Set your provider's markup (can usually be found on your billing statement)

### Run

```sh
poetry run electricity-cost-dkk
```

By default, the tool fetches today's prices. To fetch prices for a different date, provide a YYYY-MM-DD date instead - any date up to tomorrow's (Nord Pool doesn't publish further ahead).

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

Today's prices are always available, as Nord Pool publishes each day's prices one day in advance. Tomorrow's prices become available once Nord Pool publishes them, typically around 13:00. Requests made before then will return no data.

## Scope

While Nord Pool operates in other countries besides Denmark, this tool assumes Danish structures and won't work directly for other countries.

## Limitations

Grid tariffs (distribution, transmission, tax) always reflect today's currently active rate, even when you request a past or future date - eloverblik has no historical tariff data. If your grid company's rates have changed since the requested date, those components won't match what was actually billed that day; only the spot price will be historically accurate.

## Notes

Testing was done with [OK a.m.b.a.](https://www.ok.dk/) as the provider and [Radius Elnet](https://radiuselnet.dk/) as the grid company.

### Price discrepancy

If totals deviate from what you see on your provider's mobile app, website, or billing statement, it may be because they use a different data source, calculation method or fee structure.