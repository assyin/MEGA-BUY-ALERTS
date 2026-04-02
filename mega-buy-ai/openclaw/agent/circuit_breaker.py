"""Circuit breaker for risk management."""

from datetime import datetime, timezone
from openclaw.memory.store import MemoryStore


class CircuitBreaker:
    """Tracks losses and trips if too many in a day/week."""

    def __init__(self, memory: MemoryStore, max_daily: int = 3, max_weekly: int = 7):
        self.memory = memory
        self.max_daily = max_daily
        self.max_weekly = max_weekly

    def is_tripped(self) -> bool:
        """Check if circuit breaker is active."""
        state = self.memory.get_state()
        return state.get("circuit_breaker_active", False)

    def record_loss(self):
        """Record a loss and check if breaker should trip."""
        state = self.memory.get_state()
        daily = state.get("daily_losses", 0) + 1
        weekly = state.get("weekly_losses", 0) + 1
        tripped = daily >= self.max_daily or weekly >= self.max_weekly

        self.memory.update_state({
            "daily_losses": daily,
            "weekly_losses": weekly,
            "circuit_breaker_active": tripped,
        })

        if tripped:
            print(f"🚨 Circuit breaker TRIPPED (daily: {daily}/{self.max_daily}, weekly: {weekly}/{self.max_weekly})")

    def record_win(self):
        """Record a win."""
        state = self.memory.get_state()
        self.memory.update_state({
            "daily_wins": state.get("daily_wins", 0) + 1,
            "weekly_wins": state.get("weekly_wins", 0) + 1,
        })

    def reset_daily(self):
        """Reset daily counters (call at midnight UTC)."""
        self.memory.update_state({"daily_losses": 0, "daily_wins": 0})

    def reset_weekly(self):
        """Reset weekly counters (call Monday 00:00 UTC)."""
        self.memory.update_state({
            "weekly_losses": 0, "weekly_wins": 0,
            "circuit_breaker_active": False,
        })

    def get_status(self) -> dict:
        """Get human-readable status."""
        state = self.memory.get_state()
        return {
            "active": state.get("circuit_breaker_active", False),
            "daily_losses": f"{state.get('daily_losses', 0)}/{self.max_daily}",
            "weekly_losses": f"{state.get('weekly_losses', 0)}/{self.max_weekly}",
            "daily_wins": state.get("daily_wins", 0),
            "weekly_wins": state.get("weekly_wins", 0),
            "total_processed": state.get("total_alerts_processed", 0),
        }
