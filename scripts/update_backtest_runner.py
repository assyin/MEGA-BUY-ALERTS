#!/usr/bin/env python3
"""Update backtest_runner.py to track ignored positions"""

file_path = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/simulation/core/backtest_runner.py"

with open(file_path, "r") as f:
    content = f.read()

# Replace the _open_position method start
old_open = '''    def _open_position(
        self,
        portfolio: Portfolio,
        alert: Dict[str, Any],
        price: float
    ) -> Optional[Position]:
        """Open a position in backtest mode."""
        if not portfolio.can_open_position:
            return None

        allocation = portfolio.calculate_allocation()
        if allocation < 100:
            return None'''

new_open = '''    def _open_position(
        self,
        portfolio: Portfolio,
        alert: Dict[str, Any],
        price: float
    ) -> Optional[Position]:
        """Open a position in backtest mode."""
        if not portfolio.can_open_position:
            # Track ignored position - max trades reached
            self._save_ignored_position(
                portfolio=portfolio,
                alert=alert,
                entry_price=price,
                reason="MAX_TRADES_REACHED",
                required_capital=portfolio.calculate_allocation(),
                available_capital=portfolio.cash_available
            )
            logger.debug(
                f"[IGNORED] {alert.get('pair')} in {portfolio.name}: "
                f"max trades ({portfolio.open_positions_count}/{portfolio.max_concurrent_trades})"
            )
            return None

        allocation = portfolio.calculate_allocation()
        if allocation < 100:
            # Track ignored position - insufficient balance
            self._save_ignored_position(
                portfolio=portfolio,
                alert=alert,
                entry_price=price,
                reason="INSUFFICIENT_BALANCE",
                required_capital=allocation if allocation > 0 else portfolio.position_size_pct / 100 * portfolio.current_balance,
                available_capital=portfolio.cash_available
            )
            logger.debug(
                f"[IGNORED] {alert.get('pair')} in {portfolio.name}: "
                f"insufficient balance (need ${allocation:.2f}, have ${portfolio.cash_available:.2f})"
            )
            return None'''

content = content.replace(old_open, new_open)

# Add _save_ignored_position method before get_results
save_ignored_method = '''
    def _save_ignored_position(
        self,
        portfolio: Portfolio,
        alert: Dict[str, Any],
        entry_price: float,
        reason: str,
        required_capital: float,
        available_capital: float
    ) -> None:
        """Save an ignored position for tracking."""
        alert_ts = alert.get("alert_timestamp")
        alert_time = parse_datetime(alert_ts) if alert_ts else now_utc()

        # Calculate theoretical SL
        levels = self.exit_strategy.calculate_initial_levels(entry_price)

        ignored_data = {
            "id": generate_id(),
            "portfolio_id": portfolio.id,
            "alert_id": str(alert.get("id", "")),
            "pair": alert.get("pair", ""),
            "ignore_reason": reason,
            "alert_price": entry_price,
            "alert_timestamp": alert_time.isoformat() if hasattr(alert_time, 'isoformat') else str(alert_time),
            "required_capital": required_capital,
            "available_capital": available_capital,
            "current_price": entry_price,
            "highest_price": entry_price,
            "lowest_price": entry_price,
            "theoretical_pnl_pct": 0.0,
            "theoretical_pnl_usd": 0.0,
            "theoretical_sl": levels["initial_sl"],
            "theoretical_status": "TRACKING",
            "mode": "BACKTEST"
        }

        self.database.save_ignored_position(ignored_data)

'''

# Insert before get_results
content = content.replace("    def get_results(self)", save_ignored_method + "    def get_results(self)")

with open(file_path, "w") as f:
    f.write(content)

print("backtest_runner.py updated successfully!")
print("Added: _save_ignored_position method")
print("Modified: _open_position to track ignored positions")
