"""Market sentiment data fetcher with caching.

Fetches:
- Fear & Greed Index (alternative.me) — cached 1h
- BTC dominance / Alt Season (CoinGecko) — cached 15min
- BTC/ETH 24h change & trend (Binance) — cached 5min
"""

import time
import requests
from typing import Dict, Optional


class MarketSentiment:
    _fg_cache: Dict = {"data": None, "ts": 0}
    _dom_cache: Dict = {"data": None, "ts": 0}
    _btc_eth_cache: Dict = {"data": None, "ts": 0}
    _others_cache: Dict = {"data": None, "ts": 0}

    FG_TTL = 3600  # 1 hour
    DOM_TTL = 900  # 15 min
    BTC_ETH_TTL = 300  # 5 min
    OTHERS_TTL = 900  # 15 min

    @classmethod
    def get_fear_greed(cls) -> Optional[Dict]:
        """Get Fear & Greed Index. Returns {value, label}."""
        now = time.time()
        if cls._fg_cache["data"] and (now - cls._fg_cache["ts"]) < cls.FG_TTL:
            return cls._fg_cache["data"]

        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            data = r.json()
            if data and "data" in data and len(data["data"]) > 0:
                d = data["data"][0]
                result = {
                    "value": int(d["value"]),
                    "label": d["value_classification"],  # Extreme Fear / Fear / Neutral / Greed / Extreme Greed
                }
                cls._fg_cache = {"data": result, "ts": now}
                return result
        except Exception:
            pass

        return cls._fg_cache["data"]  # return last cached even if expired

    @classmethod
    def get_btc_dominance(cls) -> Optional[Dict]:
        """Get BTC dominance + Alt Season status. Returns {dominance, alt_season}."""
        now = time.time()
        if cls._dom_cache["data"] and (now - cls._dom_cache["ts"]) < cls.DOM_TTL:
            return cls._dom_cache["data"]

        try:
            r = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
            data = r.json()
            if data and "data" in data:
                btc_dom = data["data"]["market_cap_percentage"].get("btc", 0)
                eth_dom = data["data"]["market_cap_percentage"].get("eth", 0)
                result = {
                    "btc_dominance": round(btc_dom, 2),
                    "eth_dominance": round(eth_dom, 2),
                    "alt_season": btc_dom < 45,  # Alt season threshold
                    "btc_season": btc_dom > 65,
                }
                cls._dom_cache = {"data": result, "ts": now}
                return result
        except Exception:
            pass

        return cls._dom_cache["data"]

    @classmethod
    def get_btc_eth_data(cls) -> Optional[Dict]:
        """Get BTC + ETH 24h data + trends."""
        now = time.time()
        if cls._btc_eth_cache["data"] and (now - cls._btc_eth_cache["ts"]) < cls.BTC_ETH_TTL:
            return cls._btc_eth_cache["data"]

        result = {}
        try:
            from openclaw.pipeline.trend_engine import compute_trend
            for symbol, prefix in [("BTCUSDT", "btc"), ("ETHUSDT", "eth")]:
                # 24h price (cheap, no trend heuristic here — trend_engine does it)
                r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                                 params={"symbol": symbol}, timeout=5)
                d = r.json()
                result[f"{prefix}_price"] = float(d.get("lastPrice", 0))

                # Multi-factor trend verdict (structural EMA20/50 on closed 1H + 24h momentum)
                t = compute_trend(symbol)
                result[f"{prefix}_change_24h"] = t["details"].get("change_24h")
                result[f"{prefix}_trend_1h"] = t["label"]        # BULLISH / BULLISH_OK / NEUTRAL / BEARISH
                result[f"{prefix}_trend_score"] = t["score"]
                result[f"{prefix}_trend_bullish"] = t["bullish"]

                time.sleep(0.05)

            if result:
                cls._btc_eth_cache = {"data": result, "ts": now}
                return result
        except Exception:
            pass

        return cls._btc_eth_cache["data"]

    @classmethod
    def get_others_d(cls) -> Optional[Dict]:
        """Proxy for TradingView OTHERS.D (altcoin market cap excluding top 10).

        OTHERS.D = 100 - sum(dominance of top-10 coins by market cap).
        Also computes 7d momentum from weighted price change of non-OTHERS vs total.

        Returns:
          {
            "others_d": float,           # current OTHERS.D %
            "others_d_label": str,       # BTC/ETH_DOMINANT / BALANCED / ALT_STRONG / ALT_SEASON
            "others_7d_change": float,   # estimated 7d change in OTHERS cap (%)
            "top10_7d_avg": float,       # weighted 7d change of top-10 (approx non-OTHERS)
            "top10_symbols": list,
          }
        """
        now = time.time()
        if cls._others_cache["data"] and (now - cls._others_cache["ts"]) < cls.OTHERS_TTL:
            return cls._others_cache["data"]

        try:
            # 1. Global market cap + dominances
            rg = requests.get("https://api.coingecko.com/api/v3/global", timeout=8)
            g = rg.json().get("data", {})
            total_mc = g.get("total_market_cap", {}).get("usd")
            if not total_mc or total_mc <= 0:
                return cls._others_cache["data"]

            # 2. Top 10 coins with 7d price change
            rm = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 10,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "7d",
                },
                timeout=10,
            )
            top10 = rm.json()
            if not isinstance(top10, list) or len(top10) < 10:
                return cls._others_cache["data"]

            top10_mc = sum((c.get("market_cap") or 0) for c in top10)
            top10_dominance = round((top10_mc / total_mc) * 100, 2) if total_mc > 0 else 0
            others_d = round(100 - top10_dominance, 2)

            # Weighted 7d change of top-10
            top10_7d = None
            if top10_mc > 0:
                weighted = sum((c.get("market_cap") or 0) * (c.get("price_change_percentage_7d_in_currency") or 0) for c in top10)
                top10_7d = round(weighted / top10_mc, 2)

            # Label thresholds (conventional crypto regime zones)
            if others_d >= 18:
                label = "ALT_SEASON"
            elif others_d >= 13:
                label = "ALT_STRONG"
            elif others_d >= 8:
                label = "BALANCED"
            else:
                label = "BTC_ETH_DOMINANT"

            # Rough OTHERS 7d change: derive from non-OTHERS weighted vs total
            # If top10 7d is +X% and OTHERS.D = Y%, implicitly OTHERS 7d change can be bounded.
            # We leave the exact number to consumers; top10_7d_avg is already the useful reference.

            out = {
                "others_d": others_d,
                "others_d_label": label,
                "top10_dominance": top10_dominance,
                "top10_7d_avg": top10_7d,
                "top10_symbols": [c.get("symbol", "").upper() for c in top10],
            }
            cls._others_cache = {"data": out, "ts": now}
            return out
        except Exception:
            pass

        return cls._others_cache["data"]

    @classmethod
    def get_all(cls) -> Dict:
        """Fetch all sentiment data, return merged dict."""
        out = {}
        fg = cls.get_fear_greed()
        if fg:
            out["fear_greed_value"] = fg["value"]
            out["fear_greed_label"] = fg["label"]
        dom = cls.get_btc_dominance()
        if dom:
            out.update(dom)
        be = cls.get_btc_eth_data()
        if be:
            out.update(be)
        od = cls.get_others_d()
        if od:
            out.update(od)
        return out
