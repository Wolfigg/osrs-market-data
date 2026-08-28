# OSRS Profit Finder

A Python 3.12 market-analysis pipeline for Old School RuneScape using the OSRS Wiki / RuneLite Real-time Prices API.

The app has three separate user-facing branches built on one shared market-data core:

1. **AFK Money Makers**: ranks genuinely AFK or low-interaction processing methods using live prices, historical VWAPs, GE tax, buy limits, liquidity, realistic rates and AFK interval metrics.
2. **High Alch**: a standalone active money-making scanner for buy-and-alch opportunities. It is deliberately not used as an exit for AFK methods.
3. **Market Explorer**: current high/low observations plus 6H, 24H, 7D, 30D, 6M and 1Y historical metrics.

## Market data model

The website-style lookback buttons and API timesteps are different concepts. The V1 API exposes `5m`, `1h`, `6h` and `24h` aggregation intervals, each with up to 365 points. The collector reconstructs logical windows using the finest interval that covers the requested range:

| Lookback | API timestep |
| --- | --- |
| 6H | 5m |
| 24H | 5m |
| 7D | 1h |
| 30D | 6h |
| 6M | 24h |
| 1Y | 24h |

`high` and `low` are independent observed transaction streams, not an order book. Historical volume is a liquidity proxy, not executable depth.

## AFK branch

The AFK branch uses Grand Exchange exits only. It reports, per scenario:

- profit per cycle
- realistic and buy-limit sustainable GP/hour
- AFK interval
- interaction windows/hour
- GP per interaction window
- output units/hour
- current and historical price basis
- 24h market-share/liquidity warnings
- requirements and method assumptions

Seed methods currently included:

- Steel cannonballs with double ammo mould
- Mahogany Plank Make using autocast
- Camphor Plank Make using autocast

The method catalog is intentionally configuration-driven in `config/methods.yaml` so more AFK methods can be added without changing calculation code.

## High Alch branch

The standalone alchemy scanner performs a cheap universe scan using `/mapping` and `/latest`, then validates only the top configured candidates with historical timeseries. It includes Nature rune cost, optional Fire rune cost, buy limits, capital constraints, liquidity and price freshness.

## Generated site

```text
site/
├── index.html
├── index.json
├── health.json
├── market/
│   ├── summary.json
│   └── items/<id>.json
├── afk/
│   ├── methods.json
│   └── rankings.json
└── alchemy/
    ├── candidates.json
    └── rankings.json
```

`index.json` is the machine-readable entry point.

## Run locally

```bash
python -m venv .venv
pip install -r requirements.txt
pip install -e .
pytest
python -m osrs_market.cli collect --output site
python -m http.server --directory site 8000
```

Set a descriptive User-Agent before collection:

```bash
export OSRS_MARKET_USER_AGENT="osrs-market-data/0.2 - github.com/Wolfigg/osrs-market-data"
```

## GitHub Actions

The workflow runs on push to `master`, manually, and hourly at minute 17. It tests the package, collects live market data, validates the generated site, and deploys it with GitHub Pages.

No OSRS/Jagex credentials or API key are required.
