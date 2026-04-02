"""Tool definitions for Claude API tool-use.

Each tool is a dict matching Anthropic's tool schema.
Claude sees these descriptions and decides which to call.
"""

TOOLS = [
    {
        "name": "read_alert",
        "description": "Read full alert data from Supabase by ID. Returns pair, price, score, timeframes, all 10 MEGA BUY conditions, DI+/DI-/ADX, volume, ML decision.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string", "description": "UUID of the alert"}
            },
            "required": ["alert_id"]
        }
    },
    {
        "name": "analyze_alert",
        "description": "Compute ~197 technical indicators for a pair at the alert timestamp. Returns: 5 entry conditions (EMA100, EMA20, Cloud 1H/30M, CHoCH), 3 prerequisites (STC, trendline, 15m filter), 23 bonus filters (Fibonacci, Order Blocks, FVG, BTC/ETH correlation, Volume, RSI MTF, ADX, MACD, Bollinger, StochRSI, EMA Stack), Volume Profile (POC/VAH/VAL), and multi-TF indicators. This is the most important tool — always call it for every new alert.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pair": {"type": "string", "description": "Trading pair e.g. BTCUSDT"},
                "timestamp": {"type": "string", "description": "ISO timestamp of the alert"},
                "price": {"type": "number", "description": "Exact price at alert time"}
            },
            "required": ["pair"]
        }
    },
    {
        "name": "get_ml_prediction",
        "description": "Get ML model prediction (LightGBM + Rules Engine). Returns p_success (0-1), decision (TRADE/WATCH/SKIP), confidence, rules applied, and entry zones (SL, TP1-3).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pair": {"type": "string"},
                "price": {"type": "number"},
                "scanner_score": {"type": "integer"},
                "timeframes": {"type": "array", "items": {"type": "string"}},
                "di_plus_4h": {"type": "number"},
                "di_minus_4h": {"type": "number"},
                "adx_4h": {"type": "number"},
                "pp": {"type": "boolean"},
                "ec": {"type": "boolean"}
            },
            "required": ["pair", "price", "scanner_score"]
        }
    },
    {
        "name": "get_backtest_history",
        "description": "Get historical backtest results for a pair. Returns total trades, win rate, average P&L, best/worst trades, and strategy performance (Strategy C trailing vs Strategy D fixed TP).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pair": {"type": "string", "description": "Trading pair e.g. BTCUSDT"}
            },
            "required": ["pair"]
        }
    },
    {
        "name": "get_market_context",
        "description": "Get current market context: BTC price and trend (RSI, EMA20/50), Fear & Greed Index, and top altcoin performance. Helps assess if market conditions favor the trade.",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "get_similar_patterns",
        "description": "Search agent memory for past alerts with similar indicator profiles. Returns matching trades with their outcomes (WIN/LOSE), P&L, and pattern similarity score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pair": {"type": "string"},
                "scanner_score": {"type": "integer"},
                "has_4h": {"type": "boolean"},
                "di_plus_4h": {"type": "number"},
                "di_minus_4h": {"type": "number"},
                "adx_4h": {"type": "number"}
            },
            "required": ["scanner_score"]
        }
    },
    {
        "name": "get_portfolio_status",
        "description": "Get current simulation portfolio status: balances, open positions, P&L, win rates across all 7 portfolios (Max WR, Balanced, Big Winners, Aggressive, Balanced ML, Conservative, V5).",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "send_recommendation",
        "description": "Send a formatted recommendation message to the user via Telegram. Include inline buttons for the user to confirm, watch, or skip the trade. Call this AFTER you have completed your analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Formatted message text (Markdown)"},
                "decision": {"type": "string", "enum": ["BUY", "WATCH", "SKIP"]},
                "alert_id": {"type": "string"}
            },
            "required": ["message", "decision"]
        }
    },
    {
        "name": "record_decision",
        "description": "Record the agent's decision and reasoning to Supabase for tracking and learning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string"},
                "decision": {"type": "string", "enum": ["BUY", "WATCH", "SKIP"]},
                "confidence": {"type": "number", "description": "0-1 confidence score"},
                "reasoning": {"type": "string", "description": "Brief reasoning for the decision"}
            },
            "required": ["alert_id", "decision", "confidence", "reasoning"]
        }
    },
    {
        "name": "record_outcome",
        "description": "Record a trade outcome for learning. Called when a trade is closed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string"},
                "result": {"type": "string", "enum": ["WIN", "LOSE", "BREAKEVEN"]},
                "pnl_pct": {"type": "number"},
                "exit_reason": {"type": "string"}
            },
            "required": ["alert_id", "result", "pnl_pct"]
        }
    },
]
