#!/usr/bin/env python3
"""Update position_manager.py to track ignored positions"""

import re

file_path = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/simulation/core/position_manager.py"

with open(file_path, "r") as f:
    content = f.read()

# Find and replace the max trades check
old_max_trades = '''        if not portfolio.can_open_position:
            logger.debug(
                f"Cannot open position in {portfolio_id}: "
                f"max trades reached or disabled"
            )
            return None'''

new_max_trades = '''        if not portfolio.can_open_position:
            # Track ignored position - max trades reached
            self._save_ignored_position(
                portfolio_id=portfolio_id,
                portfolio=portfolio,
                alert=alert,
                entry_price=entry_price,
                reason="MAX_TRADES_REACHED",
                required_capital=portfolio.calculate_allocation(),
                available_capital=portfolio.cash_available
            )
            logger.info(
                f"[IGNORED] {alert.get('pair')} in {portfolio_id}: "
                f"max trades reached ({portfolio.open_positions_count}/{portfolio.max_concurrent_trades})"
            )
            return None'''

content = content.replace(old_max_trades, new_max_trades)

# Find and replace the insufficient capital check
old_capital = '''        # Calculate allocation
        allocation = portfolio.calculate_allocation()
        if allocation < 100:
            logger.debug(f"Insufficient capital in {portfolio_id}")
            return None'''

new_capital = '''        # Calculate allocation
        allocation = portfolio.calculate_allocation()
        if allocation < 100:
            # Track ignored position - insufficient balance
            self._save_ignored_position(
                portfolio_id=portfolio_id,
                portfolio=portfolio,
                alert=alert,
                entry_price=entry_price,
                reason="INSUFFICIENT_BALANCE",
                required_capital=allocation if allocation > 0 else portfolio.position_size_pct / 100 * portfolio.current_balance,
                available_capital=portfolio.cash_available
            )
            logger.info(
                f"[IGNORED] {alert.get('pair')} in {portfolio_id}: "
                f"insufficient balance (need ${allocation:.2f}, have ${portfolio.cash_available:.2f})"
            )
            return None'''

content = content.replace(old_capital, new_capital)

# Add the _save_ignored_position method and update_ignored_positions before get_stats
helper_methods = '''
    def _save_ignored_position(
        self,
        portfolio_id: str,
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
            "portfolio_id": portfolio_id,
            "alert_id": alert.get("id", ""),
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
            "mode": self.mode.value
        }

        self.database.save_ignored_position(ignored_data)

    def update_ignored_positions(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Update all tracking ignored positions with current prices.

        Returns list of ignored positions that hit theoretical SL or TP.
        """
        closed_ignored = []
        tracking_positions = self.database.get_tracking_ignored_positions()

        for ignored in tracking_positions:
            pair = ignored.get("pair")
            if pair not in prices:
                continue

            current_price = prices[pair]
            entry_price = ignored.get("alert_price", 0)
            highest = ignored.get("highest_price", entry_price)
            lowest = ignored.get("lowest_price", entry_price)
            sl_price = ignored.get("theoretical_sl", entry_price * 0.95)

            # Update highest/lowest
            if current_price > highest:
                highest = current_price
            if current_price < lowest:
                lowest = current_price

            # Calculate P&L
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            # Assume same allocation as portfolio default (12% = $240)
            theoretical_capital = 240.0
            pnl_usd = theoretical_capital * pnl_pct / 100

            # Check if SL hit
            if current_price <= sl_price:
                ignored["theoretical_status"] = "LOSS"
                ignored["theoretical_exit_price"] = sl_price
                ignored["theoretical_exit_timestamp"] = now_utc().isoformat()
                ignored["theoretical_exit_reason"] = "STOP_LOSS"
                ignored["theoretical_pnl_pct"] = -5.0  # Fixed SL at -5%
                ignored["theoretical_pnl_usd"] = -12.0  # $240 * -5%
                closed_ignored.append(ignored)
                logger.info(
                    f"[IGNORED CLOSED] {pair} in {ignored.get('portfolio_id')}: "
                    f"SL hit @ {sl_price:.4f} (Theoretical P&L: -$12.00)"
                )
            # Check if BE activation (4%)
            elif pnl_pct >= 4.0 and ignored.get("theoretical_status") == "TRACKING":
                # Move SL to BE
                sl_price = entry_price * 1.005  # BE + 0.5%
                ignored["theoretical_sl"] = sl_price
            # Check if trailing activation (15%)
            elif pnl_pct >= 15.0:
                # Trailing at 10% from highest
                trailing_sl = highest * 0.90
                if trailing_sl > sl_price:
                    sl_price = trailing_sl
                    ignored["theoretical_sl"] = sl_price
            # Check TP (50%)
            elif pnl_pct >= 50.0:
                ignored["theoretical_status"] = "WIN"
                ignored["theoretical_exit_price"] = current_price
                ignored["theoretical_exit_timestamp"] = now_utc().isoformat()
                ignored["theoretical_exit_reason"] = "TAKE_PROFIT"
                ignored["theoretical_pnl_pct"] = pnl_pct
                ignored["theoretical_pnl_usd"] = pnl_usd
                closed_ignored.append(ignored)
                logger.info(
                    f"[IGNORED CLOSED] {pair} in {ignored.get('portfolio_id')}: "
                    f"TP hit @ {current_price:.4f} (Theoretical P&L: +${pnl_usd:.2f})"
                )

            # Update in database
            ignored["current_price"] = current_price
            ignored["highest_price"] = highest
            ignored["lowest_price"] = lowest
            ignored["theoretical_pnl_pct"] = pnl_pct
            ignored["theoretical_pnl_usd"] = pnl_usd
            self.database.save_ignored_position(ignored)

        return closed_ignored

    def get_ignored_symbols(self) -> set:
        """Get all symbols with tracking ignored positions."""
        tracking = self.database.get_tracking_ignored_positions()
        return {p.get("pair") for p in tracking if p.get("pair")}

'''

# Insert helper methods before get_stats
content = content.replace("    def get_stats(self)", helper_methods + "    def get_stats(self)")

with open(file_path, "w") as f:
    f.write(content)

print("position_manager.py updated successfully!")
print("Added: _save_ignored_position, update_ignored_positions, get_ignored_symbols")
