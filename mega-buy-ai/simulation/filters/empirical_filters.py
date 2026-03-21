"""
Empirical filters based on technical indicator conditions.

These filters use conditions derived from backtesting analysis:
- Max Win Rate: 82% WR, loses big winners
- Balanced: 73% WR, keeps 67% of big gains
- Big Winners: 71% WR, keeps 92% of big gains
"""

from typing import Dict, Any, Optional

from .base_filter import BaseFilter
from ..config.settings import PortfolioConfig, FilterConditions


class EmpiricalFilter(BaseFilter):
    """
    Base class for empirical filters.

    These filters evaluate alerts based on technical indicator conditions.
    """

    def __init__(self, config: PortfolioConfig):
        super().__init__(config)
        self.conditions = config.filter_conditions or FilterConditions()

    def evaluate(self, alert: Dict[str, Any]) -> bool:
        """
        Evaluate if alert passes the empirical filter.

        Conditions checked:
        - PP (PP SuperTrend Buy)
        - EC (Entry Confirmation)
        - DI- >= threshold
        - DI+ <= threshold
        - ADX >= threshold
        - Vol >= threshold
        """
        # Get indicator values
        pp = alert.get("pp", False)
        ec = alert.get("ec", False)
        di_plus = alert.get("di_plus_4h", 0) or 0
        di_minus = alert.get("di_minus_4h", 0) or 0
        adx = alert.get("adx_4h", 0) or 0
        vol = alert.get("vol_pct_max", 0) or 0

        # Check conditions
        if self.conditions.pp and not pp:
            return False
        if self.conditions.ec and not ec:
            return False
        if di_minus < self.conditions.di_minus_min:
            return False
        if di_plus > self.conditions.di_plus_max:
            return False
        if adx < self.conditions.adx_min:
            return False
        if vol < self.conditions.vol_min:
            return False

        return True

    def get_filter_description(self) -> str:
        """Get filter description."""
        parts = []
        if self.conditions.pp:
            parts.append("PP=True")
        if self.conditions.ec:
            parts.append("EC=True")
        parts.append(f"DI-≥{self.conditions.di_minus_min}")
        parts.append(f"DI+≤{self.conditions.di_plus_max}")
        parts.append(f"ADX≥{self.conditions.adx_min}")
        parts.append(f"Vol≥{self.conditions.vol_min}%")
        return " + ".join(parts)

    def get_rejection_reason(self, alert: Dict[str, Any]) -> Optional[str]:
        """Get specific rejection reason."""
        pp = alert.get("pp", False)
        ec = alert.get("ec", False)
        di_plus = alert.get("di_plus_4h", 0) or 0
        di_minus = alert.get("di_minus_4h", 0) or 0
        adx = alert.get("adx_4h", 0) or 0
        vol = alert.get("vol_pct_max", 0) or 0

        reasons = []
        if self.conditions.pp and not pp:
            reasons.append("PP=False")
        if self.conditions.ec and not ec:
            reasons.append("EC=False")
        if di_minus < self.conditions.di_minus_min:
            reasons.append(f"DI-={di_minus:.1f}<{self.conditions.di_minus_min}")
        if di_plus > self.conditions.di_plus_max:
            reasons.append(f"DI+={di_plus:.1f}>{self.conditions.di_plus_max}")
        if adx < self.conditions.adx_min:
            reasons.append(f"ADX={adx:.1f}<{self.conditions.adx_min}")
        if vol < self.conditions.vol_min:
            reasons.append(f"Vol={vol:.1f}%<{self.conditions.vol_min}%")

        if reasons:
            return f"[{self.portfolio_name}] " + ", ".join(reasons)
        return None


class MaxWRFilter(EmpiricalFilter):
    """
    Max Win Rate filter.

    Performance: 82% Win Rate, but loses big winners.

    Conditions:
    - PP = True
    - EC = True
    - DI- >= 22
    - DI+ <= 25
    - ADX >= 35 (very strong trend)
    - Vol >= 100%
    """

    def __init__(self, config: Optional[PortfolioConfig] = None):
        if config is None:
            config = PortfolioConfig(
                id="max_wr",
                name="Max Win Rate",
                type="empirical_filter",
                filter_conditions=FilterConditions(
                    pp=True,
                    ec=True,
                    di_minus_min=22.0,
                    di_plus_max=25.0,
                    adx_min=35.0,
                    vol_min=100.0
                )
            )
        super().__init__(config)


class BalancedFilter(EmpiricalFilter):
    """
    Balanced filter.

    Performance: 73% Win Rate, keeps 67% of big gains.

    Conditions:
    - PP = True
    - EC = True
    - DI- >= 22
    - DI+ <= 20 (stricter than Max WR)
    - ADX >= 21 (moderate trend)
    - Vol >= 100%
    """

    def __init__(self, config: Optional[PortfolioConfig] = None):
        if config is None:
            config = PortfolioConfig(
                id="balanced_filter",
                name="Équilibré",
                type="empirical_filter",
                filter_conditions=FilterConditions(
                    pp=True,
                    ec=True,
                    di_minus_min=22.0,
                    di_plus_max=20.0,
                    adx_min=21.0,
                    vol_min=100.0
                )
            )
        super().__init__(config)


class BigWinnersFilter(EmpiricalFilter):
    """
    Big Winners filter.

    Performance: 71% Win Rate, keeps 92% of big gains.

    Conditions:
    - PP = True
    - EC = True
    - DI- >= 22
    - DI+ <= 25
    - ADX >= 21 (more relaxed than Max WR)
    - Vol >= 100%
    """

    def __init__(self, config: Optional[PortfolioConfig] = None):
        if config is None:
            config = PortfolioConfig(
                id="big_winners",
                name="Gros Gagnants",
                type="empirical_filter",
                filter_conditions=FilterConditions(
                    pp=True,
                    ec=True,
                    di_minus_min=22.0,
                    di_plus_max=25.0,
                    adx_min=21.0,
                    vol_min=100.0
                )
            )
        super().__init__(config)


def create_filter_from_config(config: PortfolioConfig) -> Optional[EmpiricalFilter]:
    """
    Create an empirical filter from portfolio configuration.

    Args:
        config: Portfolio configuration

    Returns:
        Configured filter or None
    """
    if config.type != "empirical_filter":
        return None

    if config.filter_conditions is None:
        return None

    return EmpiricalFilter(config)
