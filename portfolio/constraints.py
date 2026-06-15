"""
Portfolio Constraints
---------------------
Defines hard limits enforced during portfolio construction.
"""

CONSTRAINTS = {
    # Maximum weight for any single asset
    "max_single_asset": 0.15,

    # Maximum weight for any single sector
    "max_single_sector": 0.35,

    # Minimum number of assets per sleeve (if sleeve is populated)
    "min_assets_per_sleeve": 2,

    # AVOID assets cannot appear in any sleeve
    "allow_avoid_in_portfolio": False,

    # Minimum ACS to appear in Core sleeve
    "min_acs_for_core_sleeve": 0.75,

    # Minimum ACS to appear in Growth sleeve
    "min_acs_for_growth_sleeve": 0.55,
}
