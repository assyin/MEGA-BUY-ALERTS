"""
ML-based filters using p_success thresholds.

These filters use the ML model's probability prediction to filter alerts:
- Aggressive: p_success >= 0.30 (~90% of alerts)
- Balanced: p_success >= 0.50 (~55% of alerts)
- Conservative: p_success >= 0.70 (~10% of alerts)
"""

from typing import Dict, Any, Optional

from .base_filter import BaseFilter
from ..config.settings import PortfolioConfig


class MLFilter(BaseFilter):
    """
    ML-based filter using p_success threshold.
    """

    def __init__(self, config: PortfolioConfig):
        super().__init__(config)
        self.threshold = config.threshold or 0.50

    def evaluate(self, alert: Dict[str, Any]) -> bool:
        """
        Evaluate if alert passes the p_success threshold.

        Args:
            alert: Alert data with p_success field

        Returns:
            True if p_success >= threshold
        """
        p_success = alert.get("p_success")

        if p_success is None:
            # If no ML prediction available, skip this filter
            return False

        return p_success >= self.threshold

    def get_filter_description(self) -> str:
        """Get filter description."""
        return f"p_success ≥ {self.threshold:.2f}"

    def get_rejection_reason(self, alert: Dict[str, Any]) -> Optional[str]:
        """Get rejection reason."""
        p_success = alert.get("p_success")

        if p_success is None:
            return f"[{self.portfolio_name}] No ML prediction available"

        if p_success < self.threshold:
            return f"[{self.portfolio_name}] p_success={p_success:.3f} < {self.threshold:.2f}"

        return None


class AggressiveFilter(MLFilter):
    """
    Aggressive ML filter.

    Threshold: p_success >= 0.30
    Expected trades: ~90% of alerts
    Risk: High - accepts many trades with lower probability
    """

    def __init__(self, config: Optional[PortfolioConfig] = None):
        if config is None:
            config = PortfolioConfig(
                id="aggressive",
                name="Aggressive",
                type="p_success_threshold",
                threshold=0.30
            )
        super().__init__(config)


class BalancedMLFilter(MLFilter):
    """
    Balanced ML filter.

    Threshold: p_success >= 0.50
    Expected trades: ~55% of alerts
    Risk: Moderate - balanced quantity/quality
    """

    def __init__(self, config: Optional[PortfolioConfig] = None):
        if config is None:
            config = PortfolioConfig(
                id="balanced_ml",
                name="Balanced",
                type="p_success_threshold",
                threshold=0.50
            )
        super().__init__(config)


class ConservativeFilter(MLFilter):
    """
    Conservative ML filter.

    Threshold: p_success >= 0.70
    Expected trades: ~10% of alerts
    Risk: Low - only high-probability opportunities
    """

    def __init__(self, config: Optional[PortfolioConfig] = None):
        if config is None:
            config = PortfolioConfig(
                id="conservative",
                name="Conservative",
                type="p_success_threshold",
                threshold=0.70
            )
        super().__init__(config)


def create_ml_filter_from_config(config: PortfolioConfig) -> Optional[MLFilter]:
    """
    Create an ML filter from portfolio configuration.

    Args:
        config: Portfolio configuration

    Returns:
        Configured filter or None
    """
    if config.type != "p_success_threshold":
        return None

    if config.threshold is None:
        return None

    return MLFilter(config)
