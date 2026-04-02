"""Token usage tracker for Claude API costs.

Tracks input/output tokens per request and calculates costs.
Persists usage data in Supabase or local file.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from pathlib import Path

# Pricing per 1M tokens
PRICING = {
    # Claude
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "provider": "anthropic"},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "provider": "anthropic"},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0, "provider": "anthropic"},
    # OpenAI
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-4o": {"input": 2.50, "output": 10.0, "provider": "openai"},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-4o-2024-11-20": {"input": 2.50, "output": 10.0, "provider": "openai"},
}
DEFAULT_PRICING = {"input": 0.15, "output": 0.60, "provider": "openai"}

USAGE_FILE = Path(__file__).parent.parent / "data" / "token_usage.json"


class TokenTracker:
    """Tracks Claude API token usage and costs."""

    def __init__(self):
        self._usage = self._load()

    def _load(self) -> Dict:
        """Load usage data from file."""
        if USAGE_FILE.exists():
            try:
                with open(USAGE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "total_requests": 0,
            "daily": {},
            "monthly": {},
        }

    def _save(self):
        """Save usage data to file."""
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_FILE, "w") as f:
            json.dump(self._usage, f, indent=2)

    def record(self, response, model: str = "claude-sonnet-4-20250514"):
        """Record token usage from a Claude API response."""
        usage = getattr(response, "usage", None)
        if not usage:
            return

        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)

        # Calculate cost
        pricing = PRICING.get(model, DEFAULT_PRICING)
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        # Update totals
        self._usage["total_input_tokens"] += input_tokens
        self._usage["total_output_tokens"] += output_tokens
        self._usage["total_cost_usd"] += cost
        self._usage["total_requests"] += 1

        # Update daily
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in self._usage["daily"]:
            self._usage["daily"][today] = {"input": 0, "output": 0, "cost": 0.0, "requests": 0}
        self._usage["daily"][today]["input"] += input_tokens
        self._usage["daily"][today]["output"] += output_tokens
        self._usage["daily"][today]["cost"] += cost
        self._usage["daily"][today]["requests"] += 1

        # Update monthly
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        if month not in self._usage["monthly"]:
            self._usage["monthly"][month] = {"input": 0, "output": 0, "cost": 0.0, "requests": 0}
        self._usage["monthly"][month]["input"] += input_tokens
        self._usage["monthly"][month]["output"] += output_tokens
        self._usage["monthly"][month]["cost"] += cost
        self._usage["monthly"][month]["requests"] += 1

        self._save()

    def record_openai(self, usage_dict: dict, model: str = "gpt-4o-mini"):
        """Record token usage from an OpenAI API response."""
        input_tokens = usage_dict.get("prompt_tokens", 0)
        output_tokens = usage_dict.get("completion_tokens", 0)

        pricing = PRICING.get(model, DEFAULT_PRICING)
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        self._usage["total_input_tokens"] += input_tokens
        self._usage["total_output_tokens"] += output_tokens
        self._usage["total_cost_usd"] += cost
        self._usage["total_requests"] += 1

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in self._usage["daily"]:
            self._usage["daily"][today] = {"input": 0, "output": 0, "cost": 0.0, "requests": 0}
        self._usage["daily"][today]["input"] += input_tokens
        self._usage["daily"][today]["output"] += output_tokens
        self._usage["daily"][today]["cost"] += cost
        self._usage["daily"][today]["requests"] += 1

        month = datetime.now(timezone.utc).strftime("%Y-%m")
        if month not in self._usage["monthly"]:
            self._usage["monthly"][month] = {"input": 0, "output": 0, "cost": 0.0, "requests": 0}
        self._usage["monthly"][month]["input"] += input_tokens
        self._usage["monthly"][month]["output"] += output_tokens
        self._usage["monthly"][month]["cost"] += cost
        self._usage["monthly"][month]["requests"] += 1

        self._save()

    def get_summary(self) -> Dict:
        """Get usage summary for display."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        daily = self._usage.get("daily", {}).get(today, {})
        monthly = self._usage.get("monthly", {}).get(month, {})

        total_cost = self._usage.get("total_cost_usd", 0)
        budget = 25.0  # Initial OpenAI budget
        remaining = max(0, budget - total_cost)

        return {
            "budget": {
                "initial_usd": budget,
                "spent_usd": round(total_cost, 4),
                "remaining_usd": round(remaining, 4),
                "pct_used": round(total_cost / budget * 100, 1) if budget > 0 else 0,
            },
            "today": {
                "input_tokens": daily.get("input", 0),
                "output_tokens": daily.get("output", 0),
                "cost_usd": round(daily.get("cost", 0), 4),
                "requests": daily.get("requests", 0),
            },
            "this_month": {
                "input_tokens": monthly.get("input", 0),
                "output_tokens": monthly.get("output", 0),
                "cost_usd": round(monthly.get("cost", 0), 4),
                "requests": monthly.get("requests", 0),
            },
            "all_time": {
                "input_tokens": self._usage.get("total_input_tokens", 0),
                "output_tokens": self._usage.get("total_output_tokens", 0),
                "cost_usd": round(total_cost, 4),
                "requests": self._usage.get("total_requests", 0),
            },
        }


# Singleton
_tracker: Optional[TokenTracker] = None

def get_token_tracker() -> TokenTracker:
    global _tracker
    if _tracker is None:
        _tracker = TokenTracker()
    return _tracker
