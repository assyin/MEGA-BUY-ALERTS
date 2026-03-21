    # ===== IGNORED POSITIONS =====

    def save_ignored_position(self, ignored: Dict[str, Any]) -> None:
        """Save an ignored position to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ignored_positions (
                    id, portfolio_id, alert_id, pair, ignore_reason, alert_price,
                    alert_timestamp, required_capital, available_capital,
                    current_price, highest_price, lowest_price,
                    theoretical_pnl_pct, theoretical_pnl_usd, theoretical_sl,
                    theoretical_status, theoretical_exit_price, theoretical_exit_timestamp,
                    theoretical_exit_reason, mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ignored.get("id"),
                ignored.get("portfolio_id"),
                ignored.get("alert_id"),
                ignored.get("pair"),
                ignored.get("ignore_reason"),
                ignored.get("alert_price"),
                ignored.get("alert_timestamp"),
                ignored.get("required_capital"),
                ignored.get("available_capital"),
                ignored.get("current_price"),
                ignored.get("highest_price"),
                ignored.get("lowest_price"),
                ignored.get("theoretical_pnl_pct"),
                ignored.get("theoretical_pnl_usd"),
                ignored.get("theoretical_sl"),
                ignored.get("theoretical_status", "TRACKING"),
                ignored.get("theoretical_exit_price"),
                ignored.get("theoretical_exit_timestamp"),
                ignored.get("theoretical_exit_reason"),
                ignored.get("mode", "LIVE"),
                now_utc().isoformat()
            ))

    def get_ignored_positions(
        self,
        portfolio_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get ignored positions."""
        with self.get_connection() as conn:
            query = "SELECT * FROM ignored_positions WHERE 1=1"
            params = []

            if portfolio_id:
                query += " AND portfolio_id = ?"
                params.append(portfolio_id)

            if status:
                query += " AND theoretical_status = ?"
                params.append(status)

            query += " ORDER BY alert_timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_tracking_ignored_positions(self) -> List[Dict[str, Any]]:
        """Get all ignored positions that are still being tracked."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ignored_positions WHERE theoretical_status = 'TRACKING'"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_ignored_stats(self) -> Dict[str, Any]:
        """Get statistics for ignored positions."""
        with self.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM ignored_positions").fetchone()[0]
            tracking = conn.execute(
                "SELECT COUNT(*) FROM ignored_positions WHERE theoretical_status = 'TRACKING'"
            ).fetchone()[0]
            winners = conn.execute(
                "SELECT COUNT(*) FROM ignored_positions WHERE theoretical_status = 'WIN'"
            ).fetchone()[0]
            losers = conn.execute(
                "SELECT COUNT(*) FROM ignored_positions WHERE theoretical_status = 'LOSS'"
            ).fetchone()[0]

            # Calculate total theoretical P&L
            pnl_result = conn.execute(
                "SELECT SUM(theoretical_pnl_usd) FROM ignored_positions WHERE theoretical_status IN ('WIN', 'LOSS')"
            ).fetchone()[0] or 0

            return {
                "total": total,
                "tracking": tracking,
                "winners": winners,
                "losers": losers,
                "total_theoretical_pnl": pnl_result
            }

