"""P4 — Pattern Timing Analysis.

Analyzes historical alerts to find the best hours (0-23h UTC)
and days (Mon-Sun) for MEGA BUY signals based on Win Rate.

Runs daily at 04:00 UTC and saves golden-hour insights to agent_insights.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from openclaw.config import get_settings


# Day name mapping
_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class TimingAnalyzer:
    """Discovers temporal patterns in MEGA BUY alert performance."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._results: Dict = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        """Start background loop — runs analysis daily at 04:00 UTC."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        print("⏰ TimingAnalyzer started (analysis daily at 04:00 UTC)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        """Wait until 04:00 UTC each day, then run analysis."""
        # Run once immediately on startup
        try:
            self._results = await self.analyze()
        except Exception as e:
            print(f"⚠️ TimingAnalyzer initial run error: {e}")

        while self._running:
            now = datetime.now(timezone.utc)
            target = now.replace(hour=4, minute=0, second=0, microsecond=0)
            if now.hour >= 4:
                target += timedelta(days=1)
            wait_secs = (target - now).total_seconds()
            await asyncio.sleep(wait_secs)

            if not self._running:
                break

            try:
                self._results = await self.analyze()
            except Exception as e:
                print(f"⚠️ TimingAnalyzer error: {e}")

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    async def analyze(self) -> Dict:
        """Run full timing analysis. Returns structured results dict."""
        print("⏰ TimingAnalyzer — running analysis...")

        # Fetch data from Supabase
        alerts = self._fetch_alerts()
        memories = self._fetch_memories()

        if not alerts and not memories:
            print("  ⏰ No data to analyze")
            return {"error": "no_data", "alerts_count": 0, "memories_count": 0}

        # Build outcome map from agent_memory (pair+timestamp -> outcome)
        outcome_map = self._build_outcome_map(memories)

        # Analyze by hour and day
        by_hour = self._analyze_by_hour(alerts, outcome_map)
        by_day = self._analyze_by_day(alerts, outcome_map)

        # Identify golden hours and best/worst days
        golden_hours = self._find_golden_hours(by_hour, top_n=5)
        best_day, worst_day = self._find_best_worst_day(by_day)

        # Signal distribution (all alerts, regardless of outcome)
        signal_dist_hour = self._signal_distribution_by_hour(alerts)
        signal_dist_day = self._signal_distribution_by_day(alerts)

        results = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "alerts_count": len(alerts),
            "memories_count": len(memories),
            "matched_count": sum(h.get("total", 0) for h in by_hour.values()),
            "by_hour": by_hour,
            "by_day": by_day,
            "golden_hours": golden_hours,
            "best_day": best_day,
            "worst_day": worst_day,
            "signal_distribution_hour": signal_dist_hour,
            "signal_distribution_day": signal_dist_day,
        }

        self._results = results

        # Save insights
        self._save_insights(results)

        print(f"  ⏰ Analysis complete: {len(alerts)} alerts, "
              f"{len(memories)} memories, "
              f"golden hours = {[h['hour'] for h in golden_hours]}")

        return results

    def get_results(self) -> Dict:
        """Return latest analysis results (empty dict if not yet run)."""
        return self._results

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_alerts(self) -> List[Dict]:
        """Fetch all alerts from Supabase."""
        try:
            all_alerts = []
            page_size = 1000
            offset = 0

            while True:
                result = self.sb.table("alerts") \
                    .select("id,pair,alert_timestamp,scanner_score,timeframes") \
                    .order("alert_timestamp", desc=False) \
                    .range(offset, offset + page_size - 1) \
                    .execute()
                batch = result.data or []
                all_alerts.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size

            return all_alerts
        except Exception as e:
            print(f"  ⚠️ Failed to fetch alerts: {e}")
            return []

    def _fetch_memories(self) -> List[Dict]:
        """Fetch all agent_memory entries with outcomes."""
        try:
            all_memories = []
            page_size = 1000
            offset = 0

            while True:
                result = self.sb.table("agent_memory") \
                    .select("id,pair,agent_decision,agent_confidence,outcome,pnl_pct,timestamp") \
                    .not_.is_("outcome", "null") \
                    .order("timestamp", desc=False) \
                    .range(offset, offset + page_size - 1) \
                    .execute()
                batch = result.data or []
                all_memories.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size

            return all_memories
        except Exception as e:
            print(f"  ⚠️ Failed to fetch memories: {e}")
            return []

    # ------------------------------------------------------------------
    # Processing helpers
    # ------------------------------------------------------------------

    def _build_outcome_map(self, memories: List[Dict]) -> Dict[str, Dict]:
        """Map pair -> list of outcome records (with parsed timestamps)."""
        outcome_map: Dict[str, List[Dict]] = defaultdict(list)
        for m in memories:
            pair = m.get("pair", "")
            ts_str = m.get("timestamp", "")
            if not pair or not ts_str:
                continue
            ts = self._parse_timestamp(ts_str)
            if ts is None:
                continue
            outcome_map[pair].append({
                "timestamp": ts,
                "outcome": m.get("outcome", ""),
                "pnl_pct": m.get("pnl_pct", 0) or 0,
                "decision": m.get("agent_decision", ""),
            })
        return dict(outcome_map)

    def _match_alert_to_outcome(self, alert: Dict, outcome_map: Dict) -> Optional[Dict]:
        """Find the closest outcome for an alert (within 24h window)."""
        pair = alert.get("pair", "")
        if pair not in outcome_map:
            return None

        alert_ts = self._parse_timestamp(alert.get("alert_timestamp", ""))
        if alert_ts is None:
            return None

        best_match = None
        best_delta = timedelta(hours=24)

        for outcome in outcome_map[pair]:
            delta = abs(outcome["timestamp"] - alert_ts)
            if delta < best_delta:
                best_delta = delta
                best_match = outcome

        return best_match

    @staticmethod
    def _parse_timestamp(ts_str: str) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not ts_str:
            return None
        try:
            # Handle various formats
            ts_str = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _analyze_by_hour(self, alerts: List[Dict], outcome_map: Dict) -> Dict[int, Dict]:
        """Group matched alerts by UTC hour and calculate stats."""
        buckets: Dict[int, List[Dict]] = defaultdict(list)

        for alert in alerts:
            ts = self._parse_timestamp(alert.get("alert_timestamp", ""))
            if ts is None:
                continue
            outcome = self._match_alert_to_outcome(alert, outcome_map)
            if outcome is None:
                continue
            buckets[ts.hour].append(outcome)

        results = {}
        for hour in range(24):
            outcomes = buckets.get(hour, [])
            results[hour] = self._calc_stats(outcomes, label=f"{hour:02d}:00")
        return results

    def _analyze_by_day(self, alerts: List[Dict], outcome_map: Dict) -> Dict[int, Dict]:
        """Group matched alerts by day of week (0=Mon to 6=Sun)."""
        buckets: Dict[int, List[Dict]] = defaultdict(list)

        for alert in alerts:
            ts = self._parse_timestamp(alert.get("alert_timestamp", ""))
            if ts is None:
                continue
            outcome = self._match_alert_to_outcome(alert, outcome_map)
            if outcome is None:
                continue
            buckets[ts.weekday()].append(outcome)

        results = {}
        for day in range(7):
            outcomes = buckets.get(day, [])
            results[day] = self._calc_stats(outcomes, label=_DAY_NAMES[day])
        return results

    @staticmethod
    def _calc_stats(outcomes: List[Dict], label: str = "") -> Dict:
        """Calculate WR%, avg gain, count from a list of outcome dicts."""
        total = len(outcomes)
        if total == 0:
            return {"label": label, "total": 0, "wins": 0, "wr_pct": 0.0,
                    "avg_pnl": 0.0, "avg_win_pnl": 0.0, "avg_loss_pnl": 0.0}

        wins = [o for o in outcomes if o.get("outcome") in ("WIN", "TP_HIT")]
        losses = [o for o in outcomes if o.get("outcome") in ("LOSS", "SL_HIT")]
        win_count = len(wins)
        wr = round(win_count / total * 100, 1) if total > 0 else 0.0
        avg_pnl = round(sum(o.get("pnl_pct", 0) for o in outcomes) / total, 2)
        avg_win = round(sum(o.get("pnl_pct", 0) for o in wins) / len(wins), 2) if wins else 0.0
        avg_loss = round(sum(o.get("pnl_pct", 0) for o in losses) / len(losses), 2) if losses else 0.0

        return {
            "label": label,
            "total": total,
            "wins": win_count,
            "wr_pct": wr,
            "avg_pnl": avg_pnl,
            "avg_win_pnl": avg_win,
            "avg_loss_pnl": avg_loss,
        }

    def _signal_distribution_by_hour(self, alerts: List[Dict]) -> Dict[int, int]:
        """Count raw signal distribution by hour (all alerts, not just matched)."""
        dist: Dict[int, int] = defaultdict(int)
        for alert in alerts:
            ts = self._parse_timestamp(alert.get("alert_timestamp", ""))
            if ts is not None:
                dist[ts.hour] += 1
        return {h: dist.get(h, 0) for h in range(24)}

    def _signal_distribution_by_day(self, alerts: List[Dict]) -> Dict[int, int]:
        """Count raw signal distribution by day of week."""
        dist: Dict[int, int] = defaultdict(int)
        for alert in alerts:
            ts = self._parse_timestamp(alert.get("alert_timestamp", ""))
            if ts is not None:
                dist[ts.weekday()] += 1
        return {d: dist.get(d, 0) for d in range(7)}

    # ------------------------------------------------------------------
    # Golden hours & best/worst days
    # ------------------------------------------------------------------

    def _find_golden_hours(self, by_hour: Dict[int, Dict], top_n: int = 5) -> List[Dict]:
        """Top N hours by WR% (minimum 3 samples to qualify)."""
        candidates = [
            {"hour": h, **stats}
            for h, stats in by_hour.items()
            if stats.get("total", 0) >= 3
        ]
        candidates.sort(key=lambda x: (x["wr_pct"], x["avg_pnl"]), reverse=True)
        return candidates[:top_n]

    def _find_best_worst_day(self, by_day: Dict[int, Dict]):
        """Find best and worst day by WR% (min 3 samples)."""
        qualified = [
            {"day": d, "day_name": _DAY_NAMES[d], **stats}
            for d, stats in by_day.items()
            if stats.get("total", 0) >= 3
        ]
        if not qualified:
            return None, None

        qualified.sort(key=lambda x: (x["wr_pct"], x["avg_pnl"]), reverse=True)
        return qualified[0], qualified[-1]

    # ------------------------------------------------------------------
    # Insights persistence
    # ------------------------------------------------------------------

    def _save_insights(self, results: Dict):
        """Save timing findings as strategic insights."""
        try:
            from openclaw.memory.insights import InsightsStore
            store = InsightsStore()
        except Exception as e:
            print(f"  ⚠️ Cannot create InsightsStore: {e}")
            return

        # Deactivate ALL old timing insights first (prevent duplicates)
        try:
            old = store.sb.table("agent_insights").select("id").eq("active", True).ilike("insight", "%[TIMING]%").execute()
            for o in (old.data or []):
                store.sb.table("agent_insights").update({"active": False}).eq("id", o["id"]).execute()
            if old.data:
                print(f"  ⏰ Deactivated {len(old.data)} old timing insights")
        except Exception:
            pass

        golden = results.get("golden_hours", [])
        best_day = results.get("best_day")
        worst_day = results.get("worst_day")

        # Golden hours insight
        if golden:
            hours_str = ", ".join(f"{h['hour']:02d}:00 UTC ({h['wr_pct']}% WR, n={h['total']})"
                                  for h in golden[:3])
            insight = (
                f"[TIMING] Golden hours for MEGA BUY signals: {hours_str}. "
                f"Signals during these hours have historically higher win rates. "
                f"Updated {results.get('analyzed_at', 'N/A')[:10]}."
            )
            store.add_insight(insight, category="strategy", priority=7)

        # Best day insight
        if best_day and best_day.get("wr_pct", 0) > 0:
            insight = (
                f"[TIMING] Best day for MEGA BUY: {best_day['day_name']} "
                f"({best_day['wr_pct']}% WR, avg PnL {best_day['avg_pnl']:+.1f}%, "
                f"n={best_day['total']}). "
                f"Updated {results.get('analyzed_at', 'N/A')[:10]}."
            )
            store.add_insight(insight, category="strategy", priority=7)

        # Worst day insight (warning)
        if worst_day and worst_day.get("wr_pct", 0) < 50:
            insight = (
                f"[TIMING] Worst day for MEGA BUY: {worst_day['day_name']} "
                f"({worst_day['wr_pct']}% WR, avg PnL {worst_day['avg_pnl']:+.1f}%, "
                f"n={worst_day['total']}). Consider reducing position size. "
                f"Updated {results.get('analyzed_at', 'N/A')[:10]}."
            )
            store.add_insight(insight, category="strategy", priority=7)

        # Distribution insight (busiest hours)
        dist = results.get("signal_distribution_hour", {})
        if dist:
            sorted_hours = sorted(dist.items(), key=lambda x: x[1], reverse=True)
            top3 = sorted_hours[:3]
            if top3 and top3[0][1] > 0:
                dist_str = ", ".join(f"{h:02d}:00 ({c} signals)" for h, c in top3)
                insight = (
                    f"[TIMING] Most active signal hours: {dist_str}. "
                    f"Total alerts analyzed: {results.get('alerts_count', 0)}. "
                    f"Updated {results.get('analyzed_at', 'N/A')[:10]}."
                )
                store.add_insight(insight, category="strategy", priority=5)

        print("  ⏰ Timing insights saved to agent_insights")


# ======================================================================
# Standalone execution
# ======================================================================

async def _run_standalone():
    """Run timing analysis once and print results."""
    import json

    analyzer = TimingAnalyzer()
    results = await analyzer.analyze()

    print("\n" + "=" * 70)
    print("  TIMING ANALYSIS RESULTS")
    print("=" * 70)

    print(f"\nAlerts analyzed: {results.get('alerts_count', 0)}")
    print(f"Memories with outcomes: {results.get('memories_count', 0)}")
    print(f"Matched alert-outcome pairs: {results.get('matched_count', 0)}")

    # Golden hours
    golden = results.get("golden_hours", [])
    if golden:
        print("\n--- GOLDEN HOURS (Top 5 by WR%) ---")
        for g in golden:
            print(f"  {g['label']:>6s}  WR={g['wr_pct']:5.1f}%  "
                  f"avg={g['avg_pnl']:+6.2f}%  n={g['total']}")
    else:
        print("\n--- No golden hours found (need >= 3 samples per hour) ---")

    # Best / worst day
    best = results.get("best_day")
    worst = results.get("worst_day")
    if best:
        print(f"\nBest day:  {best['day_name']} — WR={best['wr_pct']}% "
              f"avg={best['avg_pnl']:+.2f}% n={best['total']}")
    if worst:
        print(f"Worst day: {worst['day_name']} — WR={worst['wr_pct']}% "
              f"avg={worst['avg_pnl']:+.2f}% n={worst['total']}")

    # Signal distribution
    dist_h = results.get("signal_distribution_hour", {})
    if dist_h:
        print("\n--- Signal Distribution by Hour ---")
        max_count = max(dist_h.values()) if dist_h else 1
        for h in range(24):
            c = dist_h.get(h, 0)
            bar = "#" * int(c / max(max_count, 1) * 40) if c > 0 else ""
            print(f"  {h:02d}:00  {c:4d}  {bar}")

    dist_d = results.get("signal_distribution_day", {})
    if dist_d:
        print("\n--- Signal Distribution by Day ---")
        for d in range(7):
            c = dist_d.get(d, 0)
            print(f"  {_DAY_NAMES[d]:>3s}  {c:4d}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(_run_standalone())
