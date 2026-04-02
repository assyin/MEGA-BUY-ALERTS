"""Chart Generator — generates candlestick charts with key zones.

Creates TradingView-style charts with:
- Candlestick data from Binance
- Order Block zones (demand/supply)
- Volume Profile levels (POC, VAH, VAL)
- Fibonacci levels
- Entry/SL/TP markers
- EMA lines
- Cloud zones

Cost: $0 (Python local + Binance free API)
"""

import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import mplfinance as mpf
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from pathlib import Path

import requests

BINANCE_URL = "https://api.binance.com/api/v3/klines"
CHARTS_DIR = Path(__file__).parent.parent / "data" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
    """Fetch klines from Binance and format for mplfinance."""
    r = requests.get(BINANCE_URL, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
    data = r.json()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        'open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'close_time', 'qv', 'trades', 'tbv', 'tbqv', 'ignore'
    ])
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col])
    df.index = pd.DatetimeIndex(pd.to_datetime(df['open_time'], unit='ms'))
    df.index.name = 'Date'
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]


def generate_alert_chart(
    pair: str,
    analysis: Dict,
    alert_price: float = 0,
    interval: str = "1h",
    bars: int = 200,
) -> Optional[str]:
    """
    Generate a candlestick chart with key zones for an alert.

    Args:
        pair: Trading pair (e.g. BTCUSDT)
        analysis: Full analysis data from realtime_analyze
        alert_price: Price at alert time
        interval: Chart timeframe
        bars: Number of candles to show

    Returns:
        Path to saved PNG file, or None on error
    """
    try:
        # Fetch candles
        df = fetch_klines(pair, interval, bars)
        if df.empty or len(df) < 20:
            return None

        # Style
        mc = mpf.make_marketcolors(
            up='#26a69a', down='#ef5350',
            edge='inherit', wick='inherit',
            volume={'up': '#26a69a44', 'down': '#ef535044'},
        )
        style = mpf.make_mpf_style(
            marketcolors=mc,
            base_mpf_style='nightclouds',
            facecolor='#131722',
            edgecolor='#2a2e39',
            gridcolor='#2a2e39',
            gridstyle='--',
            y_on_right=True,
            rc={'font.size': 8},
        )

        # Prepare overlay lines and zones
        hlines = []
        hline_colors = []
        hline_styles = []

        # Alert price line
        if alert_price > 0:
            hlines.append(alert_price)
            hline_colors.append('#ffeb3b')
            hline_styles.append('--')

        # Extract zones from analysis
        bf = analysis.get("bonus_filters", {})
        vp = analysis.get("volume_profile", {})
        ec = analysis.get("entry_conditions", {})
        prereqs = analysis.get("prerequisites", {})

        # Volume Profile levels
        vp_1h = vp.get("1h", {})
        if isinstance(vp_1h, dict) and not vp_1h.get("error"):
            poc = vp_1h.get("poc")
            vah = vp_1h.get("vah")
            val = vp_1h.get("val")
            if poc:
                hlines.append(poc)
                hline_colors.append('#e040fb')
                hline_styles.append('-')
            if vah:
                hlines.append(vah)
                hline_colors.append('#ff5252')
                hline_styles.append(':')
            if val:
                hlines.append(val)
                hline_colors.append('#69f0ae')
                hline_styles.append(':')

        # EMA/Cloud levels
        for cond_key, color in [("ema100_1h", "#42a5f5"), ("cloud_1h", "#ab47bc")]:
            cond = ec.get(cond_key, {})
            if isinstance(cond, dict) and cond.get("value"):
                hlines.append(cond["value"])
                hline_colors.append(color)
                hline_styles.append('--')

        # Trendline — draw as oblique line if P1/P2 available, else horizontal
        tl = prereqs.get("trendline", {})
        tl_drawn = False

        # Fibonacci levels
        fib = bf.get("fib_4h", {})
        if isinstance(fib, dict) and fib.get("levels"):
            for lvl_key, price in fib["levels"].items():
                lvl = float(lvl_key)
                if 0.2 < lvl < 0.9 and price:  # Only show 23.6% to 78.6%
                    hlines.append(price)
                    hline_colors.append('#78909c')
                    hline_styles.append(':')

        # Calculate SL and TP
        entry = alert_price or df['Close'].iloc[-1]
        sl = entry * 0.95
        tp1 = entry * 1.15

        hlines.extend([sl, tp1])
        hline_colors.extend(['#f44336', '#4caf50'])
        hline_styles.extend(['-', '-'])

        # Build the addplot for hlines
        # Add padding candles on the right so bougies aren't cut off
        pad_count = 8
        last_date = df.index[-1]
        freq = pd.infer_freq(df.index) or 'h'
        pad_dates = pd.date_range(start=last_date + pd.Timedelta(hours=1), periods=pad_count, freq=freq)
        pad_df = pd.DataFrame(
            {'Open': np.nan, 'High': np.nan, 'Low': np.nan, 'Close': np.nan, 'Volume': 0},
            index=pad_dates
        )
        df_padded = pd.concat([df, pad_df])

        fig, axes = mpf.plot(
            df_padded, type='candle', style=style,
            volume=True, returnfig=True,
            figsize=(16, 8),
            title=f"\n{pair} — {interval.upper()} — MEGA BUY Analysis",
            tight_layout=True,
        )

        ax = axes[0]

        # Draw horizontal lines with labels
        price_range = df['High'].max() - df['Low'].min()
        x_right = len(df) - 1

        for price, color, ls in zip(hlines, hline_colors, hline_styles):
            # Thicker lines for SL/TP/Alert, thinner for others
            lw = 1.5 if ls == '-' else 0.8
            ax.axhline(y=price, color=color, linestyle=ls, linewidth=lw, alpha=0.8)

        # Add labels on the right side
        labels = []
        if alert_price > 0:
            labels.append((alert_price, "ALERT", '#ffeb3b'))
        if isinstance(vp_1h, dict) and not vp_1h.get("error"):
            if vp_1h.get("poc"):
                labels.append((vp_1h["poc"], "POC", '#e040fb'))
            if vp_1h.get("vah"):
                labels.append((vp_1h["vah"], "VAH", '#ff5252'))
            if vp_1h.get("val"):
                labels.append((vp_1h["val"], "VAL", '#69f0ae'))
        labels.append((sl, "SL -5%", '#f44336'))
        labels.append((tp1, "TP1 +15%", '#4caf50'))

        if isinstance(tl, dict) and tl.get("price"):
            labels.append((tl["price"], "TL", '#ff9800'))

        for cond_key, lbl, color in [("ema100_1h", "EMA100", "#42a5f5"), ("cloud_1h", "Cloud", "#ab47bc")]:
            cond = ec.get(cond_key, {})
            if isinstance(cond, dict) and cond.get("value"):
                labels.append((cond["value"], lbl, color))

        # Draw labels — stagger vertically to avoid overlap
        used_y = []
        c_range = df['High'].max() - df['Low'].min()
        label_offset = c_range * 0.008  # Small offset to avoid overlap

        for price, label, color in sorted(labels, key=lambda x: x[0], reverse=True):
            price_fmt = f"{price:.6f}" if price < 0.01 else f"{price:.4f}" if price < 1 else f"{price:.2f}"

            # Stagger if too close to another label
            display_y = price
            for uy in used_y:
                if abs(display_y - uy) < label_offset:
                    display_y = uy + label_offset
            used_y.append(display_y)

            # Alert label on the LEFT side for visibility
            if label == "ALERT":
                ax.annotate(f"  >>> {label} {price_fmt}  ",
                           xy=(x_right - 15, price), fontsize=8, color=color, fontweight='bold',
                           va='center', ha='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='#131722', edgecolor=color, linewidth=1.5, alpha=0.9))
            else:
                ax.annotate(f"  {label} {price_fmt}",
                           xy=(x_right, display_y), fontsize=7, color=color, fontweight='bold',
                           va='center', ha='left',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='#131722', edgecolor=color, alpha=0.8))

        # Draw OB zones as rectangles — extend range if needed
        chart_low = df['Low'].min()
        chart_high = df['High'].max()
        chart_range = chart_high - chart_low

        # Draw OBLIQUE trendline by finding P1/P2 timestamps in the chart data
        if isinstance(tl, dict) and tl.get("p1_time") and tl.get("p2_time"):
            p1_price = tl["p1_price"]
            p2_price = tl["p2_price"]
            p1_ts = pd.Timestamp(tl["p1_time"], unit='ms')
            p2_ts = pd.Timestamp(tl["p2_time"], unit='ms')

            # Find the closest bar index in the chart for P1 and P2
            x1 = None
            x2 = None
            for i, dt in enumerate(df.index):
                if x1 is None and dt >= p1_ts:
                    x1 = i
                if x2 is None and dt >= p2_ts:
                    x2 = i

            # Fallback if timestamps are before chart range
            if x1 is None:
                x1 = 0
            if x2 is None:
                x2 = max(x1 + 5, len(df) // 2)

            # Extend trendline to the right edge
            x3 = x_right + pad_count
            if x2 != x1:
                slope = (p2_price - p1_price) / (x2 - x1)
                p3_price = p1_price + slope * (x3 - x1)
            else:
                p3_price = p2_price

            ax.plot([x1, x2, x3], [p1_price, p2_price, p3_price],
                   color='#ff9800', linewidth=1.5, linestyle='-', alpha=0.9)
            # P1 and P2 markers
            ax.plot(x1, p1_price, 'o', color='#ff9800', markersize=5, alpha=0.8)
            ax.plot(x2, p2_price, 'o', color='#ff9800', markersize=5, alpha=0.8)
            tl_tf = tl.get("tf", "").upper()
            ax.annotate(f" TL {tl_tf}", xy=(x3, p3_price), fontsize=7, color='#ff9800',
                       fontweight='bold', va='center',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='#131722', edgecolor='#ff9800', alpha=0.8))
            tl_drawn = True

        elif isinstance(tl, dict) and tl.get("p1_price") and tl.get("p2_price"):
            # Fallback: no timestamps, use approximate positions
            p1_price = tl["p1_price"]
            p2_price = tl["p2_price"]
            x1 = 5
            x2 = len(df) // 2
            x3 = x_right + pad_count
            if x2 != x1:
                slope = (p2_price - p1_price) / (x2 - x1)
                p3_price = p1_price + slope * (x3 - x1)
            else:
                p3_price = p2_price
            ax.plot([x1, x2, x3], [p1_price, p2_price, p3_price],
                   color='#ff9800', linewidth=1.5, linestyle='-', alpha=0.8)
            tl_drawn = True

        elif isinstance(tl, dict) and tl.get("price"):
            # Last fallback: horizontal trendline
            hlines.append(tl["price"])
            hline_colors.append('#ff9800')
            hline_styles.append('-')

        for tf_key in ["ob_1h", "ob_4h"]:
            ob_data = bf.get(tf_key, {})
            if isinstance(ob_data, dict):
                # Only draw the 2 closest OB per TF
                for i, block in enumerate(ob_data.get("blocks", [])[:2]):
                    zh = block.get("zone_high", 0)
                    zl = block.get("zone_low", 0)
                    if not zh or not zl:
                        continue
                    if zl > chart_high * 1.15 or zh < chart_low * 0.85:
                        continue
                    is_4h = "4h" in tf_key
                    color = '#00bcd4' if not is_4h else '#9c27b0'
                    alpha = 0.08  # Very light fill
                    rect = patches.Rectangle(
                        (0, zl), x_right + pad_count, zh - zl,
                        linewidth=1.2, edgecolor=color, facecolor=color, alpha=alpha
                    )
                    ax.add_patch(rect)
                    side = "OB 4H" if is_4h else "OB 1H"
                    mitigated = " M" if block.get("mitigated") else ""
                    ax.annotate(f" {side}{mitigated}",
                               xy=(3 if i == 0 else x_right // 2, (zh + zl) / 2),
                               fontsize=6, color=color, alpha=0.6, va='center')

        # Legend box
        legend_items = [
            ("-- Alert", '#ffeb3b'),
            ("-- POC", '#e040fb'),
            (".. VAH", '#ff5252'),
            (".. VAL", '#69f0ae'),
            ("-- EMA100", '#42a5f5'),
            ("-- Trendline", '#ff9800'),
            ("[] OB Zone", '#26a69a'),
            ("-- SL", '#f44336'),
            ("-- TP1", '#4caf50'),
        ]
        legend_text = "  |  ".join([f"{name}" for name, _ in legend_items])
        fig.text(0.5, 0.01, legend_text, ha='center', fontsize=6, color='#9e9e9e')

        # Conditions summary
        cond_count = ec.get("count", 0)
        cond_total = ec.get("total", 5)
        fig.text(0.02, 0.97, f"Conditions: {cond_count}/{cond_total}  |  SL: -5%  |  TP1: +15%",
                ha='left', fontsize=7, color='#9e9e9e', transform=fig.transFigure)

        # Save
        filename = f"{pair}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = CHARTS_DIR / filename
        fig.savefig(str(filepath), dpi=150, bbox_inches='tight',
                   facecolor='#131722', edgecolor='none')
        plt.close(fig)

        return str(filepath)

    except Exception as e:
        print(f"⚠️ Chart generation error for {pair}: {e}")
        return None
