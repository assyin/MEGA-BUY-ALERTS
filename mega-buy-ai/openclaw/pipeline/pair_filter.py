"""Centralized pair filter — excludes stablecoins, delisted, and non-trading pairs.

Uses Binance exchangeInfo API to get ONLY actively tradable pairs.
Caches the result for 1 hour to avoid excessive API calls.
"""

import time
import requests
from typing import Set, List

# Stablecoins, pegged assets, forex, wrapped tokens
STABLECOIN_BLACKLIST = {
    # USD stablecoins
    "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "DAIUSDT",
    "USDPUSDT", "USTCUSDT", "LUSDUSDT", "FRAXUSDT", "USDDUSDT",
    "USDTUSDT", "USD1USDT", "USDEUSDT", "PYUSDUSDT", "GUSDUSDT",
    "USDYUSDT", "CEURUSDT", "EURCUSDT",
    # Gold / commodity pegged
    "PAXGUSDT", "XAUTUSDT",
    # Forex pegged
    "EURUSDT", "GBPUSDT", "JPYUSDT", "AUDUSDT", "TRYUSDT",
    # Wrapped / bridged that track 1:1
    "WBTCUSDT", "WBETHUSDT", "BETHUSDT", "STETHUSDT", "CBETHUSDT",
}

BINANCE_API = "https://api.binance.com"

# Cache
_trading_pairs: Set[str] = set()
_last_refresh: float = 0
_cache_ttl: float = 3600  # 1 hour


def get_trading_pairs(force_refresh: bool = False) -> Set[str]:
    """Get all USDT pairs that are actively TRADING on Binance.

    Excludes:
    - Delisted pairs (status = BREAK)
    - Stablecoins/pegged assets (BLACKLIST)
    - Non-USDT pairs

    Cached for 1 hour.
    """
    global _trading_pairs, _last_refresh

    if not force_refresh and _trading_pairs and (time.time() - _last_refresh) < _cache_ttl:
        return _trading_pairs

    try:
        r = requests.get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=15)
        data = r.json()
        symbols = data.get("symbols", [])

        active = set()
        for s in symbols:
            symbol = s.get("symbol", "")
            status = s.get("status", "")
            if (symbol.endswith("USDT")
                and status == "TRADING"
                and symbol not in STABLECOIN_BLACKLIST):
                active.add(symbol)

        _trading_pairs = active
        _last_refresh = time.time()
        print(f"📋 Pair filter refreshed: {len(active)} tradable USDT pairs (excluded {len(symbols) - len(active)} non-trading/stablecoins)")
        return active

    except Exception as e:
        print(f"⚠️ Pair filter refresh error: {e}")
        # Return cached if available
        return _trading_pairs if _trading_pairs else set()


def is_tradable(pair: str) -> bool:
    """Check if a pair is currently tradable."""
    pairs = get_trading_pairs()
    return pair in pairs


def filter_pairs(pairs: List[str]) -> List[str]:
    """Filter a list of pairs to only tradable ones."""
    trading = get_trading_pairs()
    return [p for p in pairs if p in trading]
