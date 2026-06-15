"""
Portfolio Constraints
---------------------
Defines the limits applied during portfolio construction.

Enforcement model:
  HARD (changes the allocation):
    - max_single_asset            : water-fill cap; excess redistributed
    - allow_avoid_in_portfolio    : AVOID assets are never allocated
    - min_acs_for_core_sleeve     : below-floor assets are kept out of Core
    - min_acs_for_growth_sleeve   : below-floor assets are kept out of Growth
  SOFT (surfaced as a warning, not auto-rebalanced):
    - max_single_sector           : flagged when a sector exceeds the cap
    - min_assets_per_sleeve       : flagged when a populated sleeve is too thin
"""

CONSTRAINTS = {
    # Maximum weight for any single asset
    "max_single_asset": 0.15,

    # Maximum weight for any single sector (soft — surfaced as a warning)
    "max_single_sector": 0.35,

    # Minimum number of assets per sleeve (soft — surfaced as a warning)
    "min_assets_per_sleeve": 2,

    # AVOID assets cannot appear in any sleeve
    "allow_avoid_in_portfolio": False,

    # Minimum ACS to appear in Core sleeve
    "min_acs_for_core_sleeve": 0.75,

    # Minimum ACS to appear in Growth sleeve
    "min_acs_for_growth_sleeve": 0.55,

    # An asset routes to the Defensive sleeve when its structural risk is at or
    # below this level and its ACS is below the Growth floor — i.e. stable,
    # low-risk ballast rather than a high-conviction return driver.
    "defensive_srs_max": 0.10,
}
