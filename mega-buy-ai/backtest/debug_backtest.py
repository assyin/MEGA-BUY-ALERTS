#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(line_buffering=True)  # Force line buffering

sys.path.insert(0, '.')
from datetime import datetime
from api.engine import BacktestEngine, get_binance_klines, detect_mega_buy_full, DEFAULT_CONFIG
from api.models import SessionLocal, BacktestRun, Alert

def progress(msg):
    print(f'[PROGRESS] {msg}', flush=True)

symbol = 'SOLUSDT'
start = '2026-02-01'
end = '2026-02-28'

print(f'Starting backtest for {symbol}...', flush=True)

# First verify detection works
print('Testing MEGA BUY detection...', flush=True)
df_1h = get_binance_klines(symbol, '1h', start, end)
mega_buys, _, _, _, _ = detect_mega_buy_full(df_1h, '1H', DEFAULT_CONFIG)
print(f'Detected {len(mega_buys)} MEGA BUY signals on 1H', flush=True)

# Count how many are in date range
start_dt = datetime.strptime(start, '%Y-%m-%d')
end_dt = datetime.strptime(end, '%Y-%m-%d')
in_range = [mb for mb in mega_buys if start_dt <= mb['datetime'] < end_dt]
print(f'In date range: {len(in_range)}', flush=True)

# Now run the actual backtest
print('\nRunning full backtest...', flush=True)
engine = BacktestEngine()

try:
    run_id = engine.run_backtest(symbol, start, end, progress)
    print(f'\nCompleted! Run ID: {run_id}', flush=True)

    # Check result
    db = SessionLocal()
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    alerts = db.query(Alert).filter(Alert.backtest_run_id == run_id).all()

    print(f'Total Alerts in DB: {len(alerts)}', flush=True)
    print(f'Stats from BacktestRun:', flush=True)
    print(f'  total_alerts: {run.total_alerts}', flush=True)
    print(f'  stc_validated: {run.stc_validated}', flush=True)
    print(f'  valid_entries: {run.valid_entries}', flush=True)
    print(f'  total_trades: {run.total_trades}', flush=True)

    db.close()

except Exception as e:
    import traceback
    print(f'ERROR: {e}', flush=True)
    traceback.print_exc()

print('Done.', flush=True)
