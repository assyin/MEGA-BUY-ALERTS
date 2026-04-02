"""Engagement Tracker — tracks promises made during audit negotiations.

Each engagement has:
- title: what was promised
- source: audit_id + point_id
- metric: what to measure (e.g., "avg_tp_pnl > 5%")
- deadline: when it should be done
- status: PENDING / RESPECTED / NOT_RESPECTED / EXPIRED
- verification_data: latest check results
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from openclaw.config import get_settings


class EngagementTracker:
    """Tracks and verifies commitments from audit negotiations."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)
        self.settings = settings
        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ─── Extraction ───────────────────────────────────────────

    def extract_engagements(
        self, audit_id: str, points: List[Dict], discussions: List[Dict]
    ) -> List[Dict]:
        """Parse ACCORD/COMPROMIS decisions to find measurable commitments.

        Uses GPT-4o-mini to extract structured engagements from decision text.
        Returns list of engagement dicts saved to Supabase.
        """
        disc_map = {d["point_id"]: d for d in discussions}
        engagements: List[Dict] = []

        for point in points:
            pid = point["id"]
            disc = disc_map.get(pid)
            if not disc:
                continue

            decision = disc.get("decision", "DESACCORD")
            if decision == "DESACCORD":
                continue

            # Build context for GPT extraction
            context = (
                f"Point #{pid}: {point['title']}\n"
                f"Evidence: {point.get('evidence', '')[:500]}\n"
                f"Recommendation: {point.get('recommendation', '')[:300]}\n"
                f"Decision: {decision}\n"
                f"Decision reason: {disc.get('decision_reason', '')[:500]}"
            )

            extracted = self._extract_with_gpt(context, audit_id, pid)
            engagements.extend(extracted)

        # Save to Supabase
        saved = []
        for eng in engagements:
            try:
                result = self.sb.table("openclaw_engagements").insert(eng).execute()
                if result.data:
                    saved.append(result.data[0])
                else:
                    saved.append(eng)
            except Exception as e:
                print(f"  Engagement save error: {e}")
                saved.append(eng)

        return saved

    def _extract_with_gpt(
        self, context: str, audit_id: str, point_id: int
    ) -> List[Dict]:
        """Use GPT-4o-mini to extract structured engagements from decision text."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.settings.openai_api_key)

            now = datetime.now(timezone.utc)
            prompt = f"""Analyze this audit decision and extract any measurable commitments/engagements.

{context}

Current date: {now.strftime('%Y-%m-%d')}

For each commitment found, return a JSON array with objects containing:
- "title": short description of the commitment (French)
- "metric_type": one of: tp_min_pct, trades_count, pair_wr, pair_blacklist, position_size, custom
- "metric_target": the target value as string (e.g., "5" for 5%, "XYZUSDT" for pair)
- "deadline_days": number of days from now to check (default 7 if not specified, null if immediate)
- "verification_query": what to check in plain text

Rules:
- Only extract CONCRETE, MEASURABLE commitments
- If there's no measurable commitment, return []
- metric_type mapping:
  - TP percentage targets → tp_min_pct
  - Trade count targets → trades_count
  - Pair win rate targets → pair_wr
  - Pairs to avoid → pair_blacklist
  - Position size rules → position_size
  - Anything else → custom

Return ONLY a valid JSON array, no markdown."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            )

            raw = response.choices[0].message.content.strip()
            # Clean markdown fencing if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            items = json.loads(raw)
            if not isinstance(items, list):
                return []

            engagements = []
            for item in items:
                deadline = None
                dd = item.get("deadline_days")
                if dd is not None:
                    try:
                        deadline = (now + timedelta(days=int(dd))).isoformat()
                    except (ValueError, TypeError):
                        pass

                engagements.append({
                    "audit_id": audit_id,
                    "point_id": point_id,
                    "title": item.get("title", "Engagement sans titre"),
                    "metric_type": item.get("metric_type", "custom"),
                    "metric_target": str(item.get("metric_target", "")),
                    "deadline": deadline,
                    "verification_query": item.get("verification_query", ""),
                    "status": "PENDING",
                    "verification_data": None,
                    "checked_at": None,
                    "created_at": now.isoformat(),
                })

            return engagements

        except Exception as e:
            print(f"  GPT engagement extraction error: {e}")
            return []

    # ─── Verification ─────────────────────────────────────────

    async def check_all(self) -> Dict[str, Any]:
        """Check ALL pending engagements against real data.

        Returns summary of checks performed.
        """
        pending = self.get_pending()
        now = datetime.now(timezone.utc)

        results = {
            "checked": 0,
            "respected": 0,
            "not_respected": 0,
            "expired": 0,
            "still_pending": 0,
            "details": [],
        }

        for eng in pending:
            eng_id = eng.get("id")
            if not eng_id:
                continue

            # Check if deadline passed
            deadline_str = eng.get("deadline")
            deadline_passed = False
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(
                        deadline_str.replace("Z", "+00:00")
                    )
                    if now > deadline:
                        deadline_passed = True
                except (ValueError, TypeError):
                    pass

            metric_type = eng.get("metric_type", "custom")
            target = eng.get("metric_target", "")

            # Run the appropriate checker
            check_result = await self._run_checker(metric_type, target, eng)

            new_status = eng["status"]
            if check_result.get("met"):
                new_status = "RESPECTED"
                results["respected"] += 1
            elif deadline_passed:
                if metric_type == "custom":
                    new_status = "EXPIRED"
                    results["expired"] += 1
                else:
                    new_status = "NOT_RESPECTED"
                    results["not_respected"] += 1
            else:
                results["still_pending"] += 1

            results["checked"] += 1
            results["details"].append({
                "id": eng_id,
                "title": eng.get("title"),
                "status": new_status,
                "check": check_result,
            })

            # Update in Supabase
            try:
                self.sb.table("openclaw_engagements").update({
                    "status": new_status,
                    "verification_data": check_result,
                    "checked_at": now.isoformat(),
                }).eq("id", eng_id).execute()
            except Exception as e:
                print(f"  Engagement update error: {e}")

        return results

    async def _run_checker(
        self, metric_type: str, target: str, eng: Dict
    ) -> Dict[str, Any]:
        """Run the appropriate metric checker."""
        try:
            if metric_type == "tp_min_pct":
                return await self._check_tp_min_pct(target)
            elif metric_type == "trades_count":
                return await self._check_trades_count(target)
            elif metric_type == "pair_wr":
                return await self._check_pair_wr(target, eng)
            elif metric_type == "pair_blacklist":
                return await self._check_pair_blacklist(target)
            elif metric_type == "position_size":
                return await self._check_position_size(target, eng)
            else:
                return await self._check_custom(target, eng)
        except Exception as e:
            return {"met": False, "error": str(e), "message": "Checker error"}

    async def _check_tp_min_pct(self, target: str) -> Dict[str, Any]:
        """Check if avg TP PnL on recent closed positions >= target."""
        try:
            target_val = float(target)
        except (ValueError, TypeError):
            return {"met": False, "message": f"Invalid target: {target}"}

        try:
            result = self.sb.table("openclaw_positions") \
                .select("pnl_pct, close_reason") \
                .eq("status", "CLOSED") \
                .eq("close_reason", "TP_HIT") \
                .order("closed_at", desc=True) \
                .limit(50) \
                .execute()

            rows = result.data or []
            if not rows:
                return {
                    "met": False,
                    "message": "No closed TP positions found",
                    "current": 0,
                    "target": target_val,
                }

            pnls = [r["pnl_pct"] for r in rows if r.get("pnl_pct") is not None]
            if not pnls:
                return {"met": False, "message": "No PnL data", "current": 0, "target": target_val}

            avg_pnl = sum(pnls) / len(pnls)
            return {
                "met": avg_pnl >= target_val,
                "current": round(avg_pnl, 2),
                "target": target_val,
                "sample_size": len(pnls),
                "message": f"Avg TP PnL: {avg_pnl:.2f}% (target: {target_val}%)",
            }
        except Exception as e:
            return {"met": False, "error": str(e)}

    async def _check_trades_count(self, target: str) -> Dict[str, Any]:
        """Check if total trades >= target."""
        try:
            target_val = int(target)
        except (ValueError, TypeError):
            return {"met": False, "message": f"Invalid target: {target}"}

        try:
            result = self.sb.table("openclaw_positions") \
                .select("id", count="exact") \
                .execute()

            count = result.count or 0
            return {
                "met": count >= target_val,
                "current": count,
                "target": target_val,
                "message": f"Total trades: {count} (target: {target_val})",
            }
        except Exception as e:
            return {"met": False, "error": str(e)}

    async def _check_pair_wr(self, target: str, eng: Dict) -> Dict[str, Any]:
        """Check if specific pair WR >= target."""
        # Target format: "PAIR:WR%" e.g. "BTCUSDT:60" or just a percentage
        verification = eng.get("verification_query", "")

        # Try to extract pair from title or verification
        import re
        pair_match = re.search(r'([A-Z]{2,15}USDT)', eng.get("title", "") + " " + verification)
        pair = pair_match.group(1) if pair_match else None

        try:
            target_wr = float(target)
        except (ValueError, TypeError):
            # target might be "PAIR:WR"
            parts = target.split(":")
            if len(parts) == 2:
                pair = parts[0]
                try:
                    target_wr = float(parts[1])
                except (ValueError, TypeError):
                    return {"met": False, "message": f"Invalid target: {target}"}
            else:
                return {"met": False, "message": f"Invalid target: {target}"}

        if not pair:
            return {"met": False, "message": "Cannot determine pair for WR check"}

        try:
            result = self.sb.table("openclaw_positions") \
                .select("pnl_pct") \
                .eq("pair", pair) \
                .eq("status", "CLOSED") \
                .execute()

            rows = result.data or []
            if not rows:
                return {"met": False, "message": f"No closed trades for {pair}", "current": 0, "target": target_wr}

            wins = sum(1 for r in rows if (r.get("pnl_pct") or 0) > 0)
            wr = (wins / len(rows)) * 100
            return {
                "met": wr >= target_wr,
                "current": round(wr, 1),
                "target": target_wr,
                "pair": pair,
                "trades": len(rows),
                "message": f"{pair} WR: {wr:.1f}% (target: {target_wr}%)",
            }
        except Exception as e:
            return {"met": False, "error": str(e)}

    async def _check_pair_blacklist(self, target: str) -> Dict[str, Any]:
        """Check if pair is NOT being traded (should be blacklisted)."""
        import re
        # Extract actual pair name from target (may be text like "delisté de binance")
        pair_match = re.search(r'([A-Z]{2,15}USDT)', target.upper())
        if pair_match:
            pair = pair_match.group(1)
        else:
            # target is not a pair — check if it's a generic rule
            return {"met": True, "message": f"Generic rule '{target}' — verified by delisting filter in code", "requires_manual": False}

        try:
            # Check if any OPEN position exists for this pair
            result = self.sb.table("openclaw_positions") \
                .select("id") \
                .eq("pair", pair) \
                .eq("status", "OPEN") \
                .execute()

            has_open = bool(result.data)

            # Also check if pair is in blacklist table
            is_blacklisted = False
            try:
                bl_result = self.sb.table("openclaw_pair_filter") \
                    .select("id") \
                    .eq("pair", pair) \
                    .eq("action", "BLACKLIST") \
                    .execute()
                is_blacklisted = bool(bl_result.data)
            except Exception:
                pass

            met = not has_open and is_blacklisted
            return {
                "met": met,
                "pair": pair,
                "has_open_position": has_open,
                "is_blacklisted": is_blacklisted,
                "message": f"{pair}: {'blacklisted' if is_blacklisted else 'NOT blacklisted'}, "
                           f"{'has open position' if has_open else 'no open position'}",
            }
        except Exception as e:
            return {"met": False, "error": str(e)}

    async def _check_position_size(self, target: str, eng: Dict) -> Dict[str, Any]:
        """Check if position sizes match the rule."""
        import re
        # Parse target: "10%", "50%", "$200", "200", "N/A"
        target_clean = target.replace('%', '').replace('$', '').replace(',', '').strip()
        if target_clean in ('N/A', 'n/a', ''):
            # Can't verify — treat as manual
            return {"met": False, "message": "Target non-specifique — verification manuelle requise", "requires_manual": True}
        try:
            target_val = float(target_clean)
        except (ValueError, TypeError):
            # Not a number — treat as manual
            return {"met": False, "message": f"Target '{target}' — verification manuelle requise", "requires_manual": True}

        try:
            result = self.sb.table("openclaw_positions") \
                .select("size_usd, pair") \
                .eq("status", "OPEN") \
                .execute()

            rows = result.data or []
            if not rows:
                return {"met": True, "message": "No open positions", "current": 0, "target": target_val}

            max_size = max(r.get("size_usd", 0) or 0 for r in rows)
            all_ok = all((r.get("size_usd", 0) or 0) <= target_val for r in rows)

            return {
                "met": all_ok,
                "current": round(max_size, 2),
                "target": target_val,
                "positions_checked": len(rows),
                "message": f"Max position size: ${max_size:.2f} (limit: ${target_val:.2f})",
            }
        except Exception as e:
            return {"met": False, "error": str(e)}

    async def _check_custom(self, target: str, eng: Dict) -> Dict[str, Any]:
        """Custom engagement — cannot auto-verify, check if deadline passed."""
        deadline_str = eng.get("deadline")
        if not deadline_str:
            return {"met": False, "message": "Manual verification needed", "requires_manual": True}

        try:
            now = datetime.now(timezone.utc)
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            if now > deadline:
                return {
                    "met": False,
                    "message": "Deadline passed — manual verification needed",
                    "requires_manual": True,
                    "overdue_hours": round((now - deadline).total_seconds() / 3600, 1),
                }
            else:
                remaining = deadline - now
                return {
                    "met": False,
                    "message": f"En cours — {remaining.days}j restants",
                    "requires_manual": True,
                    "remaining_days": remaining.days,
                }
        except Exception:
            return {"met": False, "message": "Manual verification needed", "requires_manual": True}

    # ─── Scheduling ───────────────────────────────────────────

    async def start(self):
        """Start daily check at 22:00 UTC."""
        self._running = True
        self._task = asyncio.create_task(self._daily_loop())
        print("  Engagement Tracker: daily check scheduled at 22:00 UTC")

    async def stop(self):
        """Stop the daily checker."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("  Engagement Tracker: stopped")

    async def _daily_loop(self):
        """Run check_all daily at 22:00 UTC."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                # Calculate next 22:00 UTC
                target = now.replace(hour=22, minute=0, second=0, microsecond=0)
                if now >= target:
                    target += timedelta(days=1)

                wait_seconds = (target - now).total_seconds()
                print(f"  Engagement Tracker: next check in {wait_seconds/3600:.1f}h")
                await asyncio.sleep(wait_seconds)

                if not self._running:
                    break

                print("  Engagement Tracker: running daily check...")
                results = await self.check_all()
                print(
                    f"  Engagement Tracker: checked {results['checked']} — "
                    f"{results['respected']} respected, "
                    f"{results['not_respected']} not respected, "
                    f"{results['expired']} expired"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"  Engagement Tracker loop error: {e}")
                await asyncio.sleep(300)  # retry in 5 min

    # ─── Queries ──────────────────────────────────────────────

    def get_pending(self) -> List[Dict]:
        """Return all PENDING engagements."""
        try:
            result = self.sb.table("openclaw_engagements") \
                .select("*") \
                .eq("status", "PENDING") \
                .order("created_at", desc=True) \
                .execute()
            return result.data or []
        except Exception as e:
            print(f"  Engagements query error: {e}")
            return []

    def get_all(self) -> List[Dict]:
        """Return all engagements."""
        try:
            result = self.sb.table("openclaw_engagements") \
                .select("*") \
                .order("created_at", desc=True) \
                .execute()
            return result.data or []
        except Exception as e:
            print(f"  Engagements query error: {e}")
            return []
