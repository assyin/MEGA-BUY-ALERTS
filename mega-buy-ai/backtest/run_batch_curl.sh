#!/bin/bash
# Batch backtest runner using dashboard API

PAIRS=$(cat data/pairs_to_retest.json | jq -r '.[]')
TOTAL=$(echo "$PAIRS" | wc -l)
START_DATE="2025-09-01"
END_DATE="2026-02-28"

echo "=============================================="
echo "  MEGA BUY AI - Batch Backtest Runner"
echo "  $TOTAL pairs to process"
echo "=============================================="
echo ""

COUNT=0
SUCCESS=0

for PAIR in $PAIRS; do
    COUNT=$((COUNT + 1))
    echo "[$COUNT/$TOTAL] Processing $PAIR..."

    # Run backtest via API
    RESULT=$(curl -s -X POST http://localhost:3002/api/backtest \
        -H "Content-Type: application/json" \
        -d "{\"symbol\": \"$PAIR\", \"start_date\": \"$START_DATE\", \"end_date\": \"$END_DATE\"}" \
        --max-time 300)

    # Check result
    if echo "$RESULT" | jq -e '.id' > /dev/null 2>&1; then
        ALERTS=$(echo "$RESULT" | jq -r '.alerts // 0')
        TRADES=$(echo "$RESULT" | jq -r '.trades // 0')
        PNL_C=$(echo "$RESULT" | jq -r '.pnl_c // 0')
        PNL_D=$(echo "$RESULT" | jq -r '.pnl_d // 0')
        echo "  ✓ Completed - Alerts: $ALERTS, Trades: $TRADES, P&L C: $PNL_C%, P&L D: $PNL_D%"
        SUCCESS=$((SUCCESS + 1))
    else
        ERROR=$(echo "$RESULT" | jq -r '.error // "Unknown error"')
        echo "  ✗ Failed: $ERROR"
    fi

    # Small delay
    sleep 2
done

echo ""
echo "=============================================="
echo "  BATCH COMPLETE"
echo "  Success: $SUCCESS/$TOTAL"
echo "=============================================="
