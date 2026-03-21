#!/usr/bin/env python3
"""Fix missing outcomes in Supabase - properly handles pagination"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / "python" / ".env")

from services.storage.supabase_client import get_supabase_client
import requests
from datetime import datetime, timedelta
import time

BINANCE_API = "https://api.binance.com"
SUCCESS_THRESHOLD = 5.0
LOOKBACK_HOURS = 168  # 7 days

def get_klines(symbol, interval, start_time, end_time):
    url = f"{BINANCE_API}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "startTime": start_time, "endTime": end_time, "limit": 1000}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def calculate_outcome(pair, entry_price, alert_timestamp):
    try:
        symbol = pair.upper()
        if not symbol.endswith("USDT"):
            symbol = symbol + "USDT"

        if 'T' in alert_timestamp:
            start_dt = datetime.fromisoformat(alert_timestamp.replace('Z', '+00:00'))
        else:
            start_dt = datetime.strptime(alert_timestamp, "%Y-%m-%d %H:%M:%S")

        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int((start_dt + timedelta(hours=LOOKBACK_HOURS)).timestamp() * 1000)
        now_ms = int(datetime.now().timestamp() * 1000)

        if start_ms > now_ms:
            return None

        end_ms = min(end_ms, now_ms)

        klines = get_klines(symbol, "15m", start_ms, end_ms)

        if not klines or len(klines) < 4:
            return None

        max_profit_pct = -999
        max_drawdown_pct = 0
        time_to_max_profit_h = 0

        for i, k in enumerate(klines):
            high = float(k[2])
            low = float(k[3])
            profit_pct = (high - entry_price) / entry_price * 100
            dd_pct = (entry_price - low) / entry_price * 100

            if profit_pct > max_profit_pct:
                max_profit_pct = profit_pct
                time_to_max_profit_h = (i + 1) * 0.25

            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

        outcome = 1 if max_profit_pct >= SUCCESS_THRESHOLD else 0

        return {
            "max_profit_pct": round(max_profit_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "time_to_max_profit_h": round(time_to_max_profit_h, 1),
            "outcome": outcome
        }
    except:
        return None

def main():
    client = get_supabase_client()

    # Get ALL alert IDs with pagination
    print("Fetching all alerts...")
    all_alerts = []
    offset = 0
    while True:
        res = client.client.table("alerts").select("id, pair, price, alert_timestamp").order("alert_timestamp", desc=True).range(offset, offset + 999).execute()
        if not res.data:
            break
        all_alerts.extend(res.data)
        offset += 1000
        if len(res.data) < 1000:
            break

    print(f"Total alerts: {len(all_alerts)}")

    # Get ALL existing outcome alert_ids with pagination
    print("Fetching existing outcomes...")
    existing_ids = set()
    offset = 0
    while True:
        res = client.client.table("outcomes").select("alert_id").range(offset, offset + 999).execute()
        if not res.data:
            break
        existing_ids.update(o["alert_id"] for o in res.data)
        offset += 1000
        if len(res.data) < 1000:
            break

    print(f"Existing outcomes: {len(existing_ids)}")

    # Find alerts without outcomes
    alerts_to_process = [a for a in all_alerts if a["id"] not in existing_ids and a.get("price")]
    print(f"Missing outcomes: {len(alerts_to_process)}")
    print()

    # Process
    success = 0
    fail = 0
    skipped = 0

    for i, alert in enumerate(alerts_to_process):
        pair = alert["pair"]
        price = alert["price"]
        timestamp = alert["alert_timestamp"]

        print(f"[{i+1}/{len(alerts_to_process)}] {pair}", end=" ", flush=True)

        result = calculate_outcome(pair, price, timestamp)

        if result:
            outcome_record = {
                "alert_id": alert["id"],
                "max_profit_pct": result["max_profit_pct"],
                "max_drawdown_pct": result["max_drawdown_pct"],
                "max_profit_time_hours": result["time_to_max_profit_h"],
                "outcome": result["outcome"]
            }

            try:
                client.client.table("outcomes").insert(outcome_record).execute()
                if result["outcome"] == 1:
                    success += 1
                    print(f"✅ +{result['max_profit_pct']:.1f}%")
                else:
                    fail += 1
                    print(f"❌ +{result['max_profit_pct']:.1f}%")
            except Exception as e:
                print(f"⚠️ {str(e)[:50]}")
                skipped += 1
        else:
            skipped += 1
            print("⏭️")

        time.sleep(0.1)

    print()
    print(f"Done! SUCCESS: {success}, FAIL: {fail}, Skipped: {skipped}")

if __name__ == "__main__":
    main()
