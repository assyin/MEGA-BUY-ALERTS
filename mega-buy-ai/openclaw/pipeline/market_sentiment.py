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

    FG_TTL = 3600  # 1 hour
    DOM_TTL = 900  # 15 min
    BTC_ETH_TTL = 300  # 5 min

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
            for symbol, prefix in [("BTCUSDT", "btc"), ("ETHUSDT", "eth")]:
                # 24h change
                r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                                 params={"symbol": symbol}, timeout=5)
                d = r.json()
                result[f"{prefix}_change_24h"] = round(float(d.get("priceChangePercent", 0)), 2)
                result[f"{prefix}_price"] = float(d.get("lastPrice", 0))

                # 1h trend (compare last close vs 24 candles ago via 1h kline)
                rk = requests.get("https://api.binance.com/api/v3/klines",
                                  params={"symbol": symbol, "interval": "1h", "limit": 1}, timeout=5)
                kd = rk.json()
                if kd and isinstance(kd, list) and len(kd) > 0:
                    o, c = float(kd[0][1]), float(kd[0][4])
                    result[f"{prefix}_trend_1h"] = "BULLISH" if c >= o else "BEARISH"

                time.sleep(0.05)

            if result:
                cls._btc_eth_cache = {"data": result, "ts": now}
                return result
        except Exception:
            pass

        return cls._btc_eth_cache["data"]

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
        return out
