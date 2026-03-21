"""
MEGA BUY AI - Feature Engineering
Calcul des features pour le modèle ML
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.market_data.binance_client import (
    get_binance_client,
    enrich_dataframe,
    calculate_rsi,
    calculate_dmi,
    calculate_atr
)

# =============================================================================
# CONFIGURATION
# =============================================================================

FEATURE_VERSION = "2.0"  # Updated with filter-based features

# =============================================================================
# FILTER THRESHOLDS (empirically validated for high win rate)
# =============================================================================

FILTER_THRESHOLDS = {
    # Max Win Rate filter (77% WR)
    "max_wr": {
        "min_di_minus": 22,
        "max_di_plus": 25,
        "min_adx": 35,
        "min_vol": 100,
        "require_pp": True,
        "require_ec": True,
    },
    # Balanced filter (75% WR, keeps 67% big winners)
    "balanced": {
        "min_di_minus": 22,
        "max_di_plus": 20,
        "min_adx": 21,
        "min_vol": 100,
        "require_pp": True,
        "require_ec": True,
    },
    # Big Winners filter (73% WR, keeps 92% big winners)
    "big_winners": {
        "min_di_minus": 22,
        "max_di_plus": 25,
        "min_adx": 21,
        "min_vol": 100,
        "require_pp": True,
        "require_ec": True,
    },
}

# Catégories de features
FEATURE_CATEGORIES = {
    "alert_basic": [
        "scanner_score",
        "nb_timeframes",
        "puissance",
        "condition_count",
    ],
    "price_action": [
        "returns_1h",
        "returns_4h",
        "returns_24h",
        "volatility_1h",
        "volatility_24h",
        "high_low_range_pct",
    ],
    "momentum": [
        "rsi_14",
        "rsi_7",
        "rsi_divergence",
        "macd_histogram",
        "macd_signal_dist",
        "stoch_k",
        "stoch_d",
    ],
    "trend": [
        "adx",
        "di_plus",
        "di_minus",
        "dmi_diff",
        "ema_9_dist",
        "ema_21_dist",
        "ema_50_dist",
        "trend_strength",
    ],
    "volume": [
        "volume_ratio",
        "volume_trend",
        "obv_slope",
    ],
    "context": [
        "hour_of_day",
        "day_of_week",
        "is_weekend",
    ],
    "mega_buy_specific": [
        "rsi_check",
        "dmi_check",
        "ast_check",
        "choch",
        "zone",
        "lazy",
        "vol",
        "st",
        "pp",
        "ec",
        "di_plus_move_max",
        "di_minus_move_max",
        "rsi_move_max",
    ],
    "filter_features": [
        # Binary threshold features
        "di_minus_ge_22",      # DI- >= 22
        "di_plus_le_25",       # DI+ <= 25
        "di_plus_le_20",       # DI+ <= 20
        "adx_ge_35",           # ADX >= 35 (strong trend)
        "adx_ge_21",           # ADX >= 21 (moderate trend)
        "vol_ge_100",          # Volume >= 100% of average
        "vol_ge_150",          # Volume >= 150% (high)
        # Composite filter passes
        "filter_max_wr",       # Passes Max Win Rate filter
        "filter_balanced",     # Passes Balanced filter
        "filter_big_winners",  # Passes Big Winners filter
        # Derived ratios
        "dmi_ratio_4h",        # DI+ / DI- ratio
        "vol_category",        # 0=low, 1=normal, 2=high, 3=explosive
        "adx_category",        # 0=weak, 1=moderate, 2=strong, 3=extreme
    ],
}


def safe_get(d: Dict, key: str, default=None):
    """Récupère une valeur de dict de manière sécurisée"""
    if d is None:
        return default
    return d.get(key, default)


def extract_alert_features(alert: Dict) -> Dict[str, float]:
    """
    Extrait les features de base depuis une alerte

    Args:
        alert: Dictionnaire de l'alerte depuis Supabase

    Returns:
        Dict de features
    """
    features = {}

    # === ALERT BASIC ===
    features["scanner_score"] = float(alert.get("scanner_score") or 0)
    features["nb_timeframes"] = float(alert.get("nb_timeframes") or 1)
    features["puissance"] = float(alert.get("puissance") or 0)

    # Compter les conditions validées
    conditions = ["rsi_check", "dmi_check", "ast_check", "choch", "zone",
                  "lazy", "vol", "st", "pp", "ec"]
    features["condition_count"] = sum(1 for c in conditions if alert.get(c))

    # === INDICATEURS 4H ===
    features["rsi_4h"] = float(alert.get("rsi") or 50)
    features["di_plus_4h"] = float(alert.get("di_plus_4h") or 0)
    features["di_minus_4h"] = float(alert.get("di_minus_4h") or 0)
    features["adx_4h"] = float(alert.get("adx_4h") or 0)
    features["dmi_diff_4h"] = features["di_plus_4h"] - features["di_minus_4h"]

    # === CONDITIONS BINAIRES ===
    for cond in conditions:
        features[cond] = 1.0 if alert.get(cond) else 0.0

    # === MOVES (max across timeframes) ===
    di_plus_moves = alert.get("di_plus_moves") or {}
    di_minus_moves = alert.get("di_minus_moves") or {}
    rsi_moves = alert.get("rsi_moves") or {}
    adx_moves = alert.get("adx_moves") or {}

    features["di_plus_move_max"] = max(
        [float(v) for v in di_plus_moves.values() if v is not None] or [0]
    )
    features["di_plus_move_15m"] = float(di_plus_moves.get("15m") or 0)
    features["di_plus_move_1h"] = float(di_plus_moves.get("1h") or 0)
    features["di_plus_move_4h"] = float(di_plus_moves.get("4h") or 0)

    features["di_minus_move_max"] = max(
        [float(v) for v in di_minus_moves.values() if v is not None] or [0]
    )
    features["rsi_move_max"] = max(
        [float(v) for v in rsi_moves.values() if v is not None] or [0]
    )
    features["adx_move_max"] = max(
        [float(v) for v in adx_moves.values() if v is not None] or [0]
    )

    # === VOLUME ===
    vol_pct = alert.get("vol_pct") or {}
    features["vol_pct_max"] = max(
        [float(v) for v in vol_pct.values() if v is not None] or [0]
    )

    # === TIMING ===
    timestamp = alert.get("alert_timestamp")
    if timestamp:
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = timestamp

        features["hour_of_day"] = float(dt.hour)
        features["day_of_week"] = float(dt.weekday())
        features["is_weekend"] = 1.0 if dt.weekday() >= 5 else 0.0
    else:
        features["hour_of_day"] = 12.0
        features["day_of_week"] = 2.0
        features["is_weekend"] = 0.0

    # === FILTER-BASED FEATURES (empirically validated) ===
    di_plus = features["di_plus_4h"]
    di_minus = features["di_minus_4h"]
    adx = features["adx_4h"]
    vol_max = features["vol_pct_max"]
    pp = features["pp"]
    ec = features["ec"]

    # Binary threshold features
    features["di_minus_ge_22"] = 1.0 if di_minus >= 22 else 0.0
    features["di_plus_le_25"] = 1.0 if di_plus <= 25 else 0.0
    features["di_plus_le_20"] = 1.0 if di_plus <= 20 else 0.0
    features["adx_ge_35"] = 1.0 if adx >= 35 else 0.0
    features["adx_ge_21"] = 1.0 if adx >= 21 else 0.0
    features["vol_ge_100"] = 1.0 if vol_max >= 100 else 0.0
    features["vol_ge_150"] = 1.0 if vol_max >= 150 else 0.0

    # Composite filter passes (all conditions must be met)
    # Max WR: PP, EC, DI- >= 22, DI+ <= 25, ADX >= 35, Vol >= 100%
    features["filter_max_wr"] = 1.0 if (
        pp == 1.0 and ec == 1.0 and
        di_minus >= 22 and di_plus <= 25 and
        adx >= 35 and vol_max >= 100
    ) else 0.0

    # Balanced: PP, EC, DI- >= 22, DI+ <= 20, ADX >= 21, Vol >= 100%
    features["filter_balanced"] = 1.0 if (
        pp == 1.0 and ec == 1.0 and
        di_minus >= 22 and di_plus <= 20 and
        adx >= 21 and vol_max >= 100
    ) else 0.0

    # Big Winners: PP, EC, DI- >= 22, DI+ <= 25, ADX >= 21, Vol >= 100%
    features["filter_big_winners"] = 1.0 if (
        pp == 1.0 and ec == 1.0 and
        di_minus >= 22 and di_plus <= 25 and
        adx >= 21 and vol_max >= 100
    ) else 0.0

    # Derived ratios
    features["dmi_ratio_4h"] = di_plus / di_minus if di_minus > 0 else 10.0

    # Volume category: 0=low (<100), 1=normal (100-150), 2=high (150-200), 3=explosive (>200)
    if vol_max < 100:
        features["vol_category"] = 0.0
    elif vol_max < 150:
        features["vol_category"] = 1.0
    elif vol_max < 200:
        features["vol_category"] = 2.0
    else:
        features["vol_category"] = 3.0

    # ADX category: 0=weak (<20), 1=moderate (20-30), 2=strong (30-50), 3=extreme (>50)
    if adx < 20:
        features["adx_category"] = 0.0
    elif adx < 30:
        features["adx_category"] = 1.0
    elif adx < 50:
        features["adx_category"] = 2.0
    else:
        features["adx_category"] = 3.0

    return features


def extract_market_features(
    symbol: str,
    timestamp: datetime = None
) -> Dict[str, float]:
    """
    Extrait les features de marché depuis Binance

    Args:
        symbol: Paire (ex: "BTCUSDT")
        timestamp: Moment de l'alerte (None = maintenant)

    Returns:
        Dict de features
    """
    features = {}
    client = get_binance_client()

    try:
        # Récupérer les klines 4H
        df_4h = client.get_klines(symbol, "4h", limit=50)
        if df_4h is not None and len(df_4h) > 0:
            df_4h = enrich_dataframe(df_4h)
            last = df_4h.iloc[-1]

            # Price action
            features["returns_4h"] = float(last.get("returns_1", 0) or 0) * 100
            features["returns_24h"] = float(df_4h["close"].pct_change(6).iloc[-1] or 0) * 100
            features["volatility_24h"] = float(last.get("volatility_20", 0) or 0)
            features["high_low_range_pct"] = float(
                (last["high"] - last["low"]) / last["close"] * 100
            ) if last["close"] > 0 else 0

            # Momentum
            features["rsi_14_market"] = float(last.get("rsi_14", 50) or 50)
            features["macd_histogram"] = float(last.get("macd_hist", 0) or 0)
            features["stoch_k"] = float(last.get("stoch_k", 50) or 50)
            features["stoch_d"] = float(last.get("stoch_d", 50) or 50)

            # Trend
            features["adx_market"] = float(last.get("adx", 0) or 0)
            features["di_plus_market"] = float(last.get("di_plus", 0) or 0)
            features["di_minus_market"] = float(last.get("di_minus", 0) or 0)
            features["ema_9_dist"] = float(last.get("ema_9_dist", 0) or 0)
            features["ema_21_dist"] = float(last.get("ema_21_dist", 0) or 0)
            features["ema_50_dist"] = float(last.get("ema_50_dist", 0) or 0)
            features["trend_strength"] = float(last.get("trend_strength", 0) or 0)

            # Volume
            features["volume_ratio"] = float(last.get("volume_ratio", 1) or 1)
            features["obv_slope"] = float(last.get("obv_slope", 0) or 0)

            # Bollinger
            features["bb_position"] = float(last.get("bb_position", 0.5) or 0.5)
            features["bb_width"] = float(last.get("bb_width", 0) or 0)

        # Récupérer les klines 1H pour plus de granularité
        df_1h = client.get_klines(symbol, "1h", limit=24)
        if df_1h is not None and len(df_1h) > 0:
            df_1h = enrich_dataframe(df_1h)
            last_1h = df_1h.iloc[-1]

            features["returns_1h"] = float(last_1h.get("returns_1", 0) or 0) * 100
            features["volatility_1h"] = float(last_1h.get("volatility_10", 0) or 0)
            features["rsi_1h"] = float(last_1h.get("rsi_14", 50) or 50)

        # Ticker 24h
        ticker = client.get_ticker(symbol)
        if ticker:
            features["price_change_24h"] = float(ticker.get("priceChangePercent", 0) or 0)
            features["volume_24h_usd"] = float(ticker.get("quoteVolume", 0) or 0)
            features["trades_24h"] = float(ticker.get("count", 0) or 0)

    except Exception as e:
        print(f"Error extracting market features for {symbol}: {e}")
        # Valeurs par défaut
        features.update({
            "returns_1h": 0, "returns_4h": 0, "returns_24h": 0,
            "volatility_1h": 0, "volatility_24h": 0,
            "rsi_14_market": 50, "adx_market": 0,
            "volume_ratio": 1, "bb_position": 0.5
        })

    return features


def compute_full_features(alert: Dict, include_market: bool = True) -> Dict[str, float]:
    """
    Calcule toutes les features pour une alerte

    Args:
        alert: Dictionnaire de l'alerte
        include_market: Inclure les features de marché (appels API)

    Returns:
        Dict complet de features
    """
    # Features de l'alerte
    features = extract_alert_features(alert)

    # Features de marché (si demandé)
    if include_market:
        symbol = alert.get("pair", "") + "USDT"
        market_features = extract_market_features(symbol)
        features.update(market_features)

    # Ajouter des features dérivées
    features["rsi_overbought"] = 1.0 if features.get("rsi_4h", 50) > 70 else 0.0
    features["rsi_oversold"] = 1.0 if features.get("rsi_4h", 50) < 30 else 0.0
    features["strong_trend"] = 1.0 if features.get("adx_4h", 0) > 25 else 0.0
    features["dmi_bullish"] = 1.0 if features.get("dmi_diff_4h", 0) > 0 else 0.0

    # Score composite
    features["momentum_score"] = (
        features.get("di_plus_move_max", 0) +
        features.get("rsi_move_max", 0) +
        features.get("condition_count", 0) * 2
    ) / 10

    return features


def get_feature_names() -> List[str]:
    """Retourne la liste ordonnée des noms de features"""
    all_features = []
    for category, features in FEATURE_CATEGORIES.items():
        all_features.extend(features)

    # Ajouter les features dérivées
    all_features.extend([
        "rsi_4h", "di_plus_4h", "di_minus_4h", "adx_4h", "dmi_diff_4h",
        "di_plus_move_15m", "di_plus_move_1h", "di_plus_move_4h",
        "vol_pct_max",
        "returns_1h", "returns_4h", "returns_24h",
        "volatility_1h", "volatility_24h",
        "rsi_14_market", "rsi_1h",
        "macd_histogram", "stoch_k", "stoch_d",
        "adx_market", "di_plus_market", "di_minus_market",
        "ema_9_dist", "ema_21_dist", "ema_50_dist",
        "volume_ratio", "obv_slope",
        "bb_position", "bb_width",
        "price_change_24h", "volume_24h_usd", "trades_24h",
        "rsi_overbought", "rsi_oversold", "strong_trend", "dmi_bullish",
        "momentum_score",
        # Filter-based features (v2.0)
        "di_minus_ge_22", "di_plus_le_25", "di_plus_le_20",
        "adx_ge_35", "adx_ge_21", "vol_ge_100", "vol_ge_150",
        "filter_max_wr", "filter_balanced", "filter_big_winners",
        "dmi_ratio_4h", "vol_category", "adx_category"
    ])

    return list(set(all_features))


def features_to_vector(features: Dict[str, float], feature_names: List[str] = None) -> np.ndarray:
    """
    Convertit un dict de features en vecteur numpy

    Args:
        features: Dict de features
        feature_names: Liste ordonnée des noms (optionnel)

    Returns:
        Array numpy
    """
    if feature_names is None:
        feature_names = get_feature_names()

    return np.array([features.get(name, 0.0) for name in feature_names])


def label_alert_outcome(alert: Dict) -> Optional[int]:
    """
    Détermine le label (succès/échec) d'une alerte

    Args:
        alert: Dictionnaire de l'alerte avec max_profit_pct

    Returns:
        1 = succès (>=5% profit), 0 = échec, None = pas de données
    """
    max_profit = alert.get("max_profit_pct")

    if max_profit is None:
        return None

    # Critère de succès: max profit >= 5%
    # (Le stop-loss à -2% sous le Low 4H est géré dans le calcul d'outcome)
    if max_profit >= 5:
        return 1
    else:
        return 0
