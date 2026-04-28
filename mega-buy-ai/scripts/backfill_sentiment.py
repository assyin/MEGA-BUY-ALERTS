#!/usr/bin/env python3
"""Backfill market sentiment data for last 7 days alerts.

Uses:
- Fear & Greed historical from alternative.me (free, public)
- BTC/ETH historical klines from Binance (free)
"""
import sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from openclaw.config import get_settings
from supabase import create_client
import requests

def get_fg_history(days=10):
    """Get Fear & Greed historical for last N days."""
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={days}", timeout=10)
        data = r.json()
        history = {}
        if data and "data" in data:
            for d in data["data"]:
                ts = int(d["timestamp"])
                date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                history[date_str] = {
                    "value": int(d["value"]),
                    "label": d["value_classification"],
                }
        return history
    except Exception as e:
        print(f"FG history error: {e}")
        return {}

def get_btc_eth_at_time(symbol: str, ts_ms: int) -> dict:
    """Get BTC/ETH 24h change and trend at a specific time."""
    try:
        # 1h candle at alert time → trend
        r = requests.get("https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1h", "limit": 1, "endTime": ts_ms}, timeout=5)
        kd = r.json()
        if not kd or not isinstance(kd, list) or len(kd) == 0:
            return {}
        o, c = float(kd[0][1]), float(kd[0][4])
        trend = "BULLISH" if c >= o else "BEARISH"

        # 24h change (close vs close 24h ago)
        r2 = requests.get("https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1h", "limit": 1, "endTime": ts_ms - 24*3600*1000}, timeout=5)
        kd2 = r2.json()
        change = 0
        if kd2 and isinstance(kd2, list) and len(kd2) > 0:
            old_price = float(kd2[0][4])
            if old_price > 0:
                change = round((c / old_price - 1) * 100, 2)

        return {"trend": trend, "change": change, "price": c}
    except:
        return {}

def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Load all alerts last 7 days
    all_alerts = []
    for offset in range(0, 3000, 500):
        r = sb.table('agent_memory') \
            .select('id,pair,timestamp,features_fingerprint') \
            .gte('timestamp', since) \
            .order('timestamp', desc=False) \
            .range(offset, offset + 499) \
            .execute()
        all_alerts.extend(r.data or [])
        if len(r.data or []) < 500: break

    # Filter only those without sentiment data
    to_update = [d for d in all_alerts if not (d.get('features_fingerprint') or {}).get('fear_greed_value')]
    print(f"Total alerts 7d: {len(all_alerts)}")
    print(f"Missing sentiment: {len(to_update)}")

    # Get FG history (10 days to be safe)
    fg_hist = get_fg_history(10)
    print(f"FG history days: {len(fg_hist)}")

    updated = 0
    errors = 0

    # Cache BTC/ETH data per timestamp (round to nearest hour)
    btc_cache = {}
    eth_cache = {}

    for i, d in enumerate(to_update):
        if i % 50 == 0:
            print(f"[{i}/{len(to_update)}]...")

        ts = d.get('timestamp', '')
        fp = d.get('features_fingerprint') or {}

        try:
            ts_dt = datetime.fromisoformat(ts.replace('+00:00', '+00:00'))
            ts_ms = int(ts_dt.timestamp() * 1000)
            date_str = ts_dt.strftime("%Y-%m-%d")
            hour_key = ts_dt.strftime("%Y-%m-%d-%H")

            updates = {}

            # Fear & Greed
            if date_str in fg_hist:
                updates["fear_greed_value"] = fg_hist[date_str]["value"]
                updates["fear_greed_label"] = fg_hist[date_str]["label"]

            # BTC data (cached per hour)
            if hour_key not in btc_cache:
                btc_cache[hour_key] = get_btc_eth_at_time("BTCUSDT", ts_ms)
                time.sleep(0.05)
            btc_data = btc_cache[hour_key]
            if btc_data:
                updates["btc_trend_1h"] = btc_data["trend"]
                updates["btc_change_24h"] = btc_data["change"]
                updates["btc_price"] = btc_data["price"]

            # ETH data (cached per hour)
            if hour_key not in eth_cache:
                eth_cache[hour_key] = get_btc_eth_at_time("ETHUSDT", ts_ms)
                time.sleep(0.05)
            eth_data = eth_cache[hour_key]
            if eth_data:
                updates["eth_trend_1h"] = eth_data["trend"]
                updates["eth_change_24h"] = eth_data["change"]
                updates["eth_price"] = eth_data["price"]

            if updates:
                fp.update(updates)
                sb.table('agent_memory').update({'features_fingerprint': fp}).eq('id', d['id']).execute()
                updated += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ERROR: {e}")

    print(f"\nDone! Updated: {updated} | Errors: {errors}")
    print(f"BTC cached hours: {len(btc_cache)}")
    print(f"ETH cached hours: {len(eth_cache)}")

if __name__ == "__main__":
    main()
