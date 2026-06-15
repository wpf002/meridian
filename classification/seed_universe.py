"""
Universe Seed
-------------
Initial watchlist for Meridian — a diversified set of assets across sectors.
Seeded into the `assets` table on first boot (only if the universe is empty),
so the scoring and portfolio commands have a universe to operate on.
"""

from classification.asset_universe import AssetUniverse


# (ticker, name, sector, asset_class)
SEED_ASSETS = [
    # Mega-cap technology
    ("NVDA", "NVIDIA Corp", "Technology", "equity"),
    ("AAPL", "Apple Inc", "Technology", "equity"),
    ("MSFT", "Microsoft Corp", "Technology", "equity"),
    ("GOOGL", "Alphabet Inc", "Technology", "equity"),
    ("META", "Meta Platforms", "Technology", "equity"),
    ("AMZN", "Amazon.com Inc", "Consumer Discretionary", "equity"),
    # Semiconductors
    ("AMD", "Advanced Micro Devices", "Technology", "equity"),
    ("AVGO", "Broadcom Inc", "Technology", "equity"),
    ("TSM", "Taiwan Semiconductor", "Technology", "equity"),
    ("ASML", "ASML Holding", "Technology", "equity"),
    # Financials
    ("JPM", "JPMorgan Chase", "Financials", "equity"),
    ("BAC", "Bank of America", "Financials", "equity"),
    ("GS", "Goldman Sachs", "Financials", "equity"),
    ("V", "Visa Inc", "Financials", "equity"),
    # Energy
    ("XOM", "Exxon Mobil", "Energy", "equity"),
    ("CVX", "Chevron Corp", "Energy", "equity"),
    # Healthcare
    ("UNH", "UnitedHealth Group", "Healthcare", "equity"),
    ("LLY", "Eli Lilly", "Healthcare", "equity"),
    ("JNJ", "Johnson & Johnson", "Healthcare", "equity"),
    # Consumer staples / defensive
    ("PG", "Procter & Gamble", "Consumer Staples", "equity"),
    ("KO", "Coca-Cola Co", "Consumer Staples", "equity"),
    ("COST", "Costco Wholesale", "Consumer Staples", "equity"),
    ("WMT", "Walmart Inc", "Consumer Staples", "equity"),
    # Broad / rates ETFs
    ("SPY", "SPDR S&P 500 ETF", "Index", "etf"),
    ("TLT", "iShares 20+ Year Treasury", "Fixed Income", "etf"),
]


def seed_universe(db_path: str = None) -> int:
    """
    Seed the asset universe if it is currently empty.
    Returns the number of assets added (0 if already populated).
    """
    universe = AssetUniverse(db_path) if db_path else AssetUniverse()
    if universe.get_all(active_only=False):
        return 0

    for ticker, name, sector, asset_class in SEED_ASSETS:
        universe.add(ticker, name, sector=sector, asset_class=asset_class)
    return len(SEED_ASSETS)
