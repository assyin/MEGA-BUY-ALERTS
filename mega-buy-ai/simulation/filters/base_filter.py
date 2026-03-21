"""
Base filter class for portfolio selection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..config.settings import PortfolioConfig


class BaseFilter(ABC):
    """
    Abstract base class for portfolio filters.

    A filter determines whether an alert should trigger an entry
    for a specific portfolio.
    """

    def __init__(self, config: PortfolioConfig):
        """
        Initialize filter.

        Args:
            config: Portfolio configuration
        """
        self.config = config
        self.portfolio_id = config.id
        self.portfolio_name = config.name

    @abstractmethod
    def evaluate(self, alert: Dict[str, Any]) -> bool:
        """
        Evaluate if an alert passes the filter.

        Args:
            alert: Alert data with indicators

        Returns:
            True if alert passes the filter
        """
        pass

    @abstractmethod
    def get_filter_description(self) -> str:
        """
        Get a human-readable description of the filter.

        Returns:
            Filter description
        """
        pass

    def get_rejection_reason(self, alert: Dict[str, Any]) -> Optional[str]:
        """
        Get the reason why an alert was rejected.

        Args:
            alert: Alert data

        Returns:
            Rejection reason or None if alert passes
        """
        if self.evaluate(alert):
            return None
        return f"Did not pass {self.portfolio_name} filter"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(portfolio={self.portfolio_id})"
