import { NextRequest, NextResponse } from "next/server"
import { spawn } from "child_process"
import path from "path"

const BACKTEST_DIR = path.join(process.cwd(), "..", "backtest")
const PYTHON_PATH = path.join(BACKTEST_DIR, "venv", "bin", "python")

async function runPython(script: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON_PATH, ["-c", script], {
      cwd: BACKTEST_DIR
    })

    let stdout = ""
    let stderr = ""

    proc.stdout.on("data", (data) => {
      stdout += data.toString()
    })

    proc.stderr.on("data", (data) => {
      stderr += data.toString()
    })

    proc.on("close", (code) => {
      if (code === 0) {
        resolve(stdout)
      } else {
        reject(new Error(stderr || `Process exited with code ${code}`))
      }
    })
  })
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get("id")

    if (!id) {
      return NextResponse.json({ error: "Missing id" }, { status: 400 })
    }

    const script = `
import json
import sys
sys.path.insert(0, '.')
from api.models import SessionLocal, Trade, Alert

db = SessionLocal()
trades = db.query(Trade).filter(Trade.backtest_run_id == ${id}).order_by(Trade.alert_datetime).all()

# Build alert lookup for mega_buy_details
alert_ids = [t.alert_id for t in trades if t.alert_id]
alerts_map = {}
if alert_ids:
    alerts = db.query(Alert).filter(Alert.id.in_(alert_ids)).all()
    alerts_map = {a.id: a for a in alerts}

result = []
for t in trades:
    result.append({
        'id': t.id,
        'alert_datetime': t.alert_datetime.isoformat() if t.alert_datetime else None,
        'timeframe': t.timeframe,
        'alert_price': t.alert_price,
        'entry_datetime': t.entry_datetime.isoformat() if t.entry_datetime else None,
        'entry_price': t.entry_price,
        'sl_price': t.sl_price,
        'tp1_price': t.tp1_price,
        'tp2_price': t.tp2_price,
        'trailing_activation_price': t.trailing_activation_price,
        'highest_price': t.highest_price,
        'trailing_active': t.trailing_active,
        'trailing_sl': t.trailing_sl,
        'exit_datetime_c': t.exit_datetime_c.isoformat() if t.exit_datetime_c else None,
        'exit_price_c': t.exit_price_c,
        'exit_reason_c': t.exit_reason_c,
        'pnl_c': t.pnl_c,
        'tp1_hit': t.tp1_hit,
        'tp2_hit': t.tp2_hit,
        'exit_datetime_d': t.exit_datetime_d.isoformat() if t.exit_datetime_d else None,
        'exit_price_d': t.exit_price_d,
        'exit_reason_d': t.exit_reason_d,
        'pnl_d_tp1': t.pnl_d_tp1,
        'pnl_d_tp2': t.pnl_d_tp2,
        'pnl_d': t.pnl_d,
        # Post-SL Recovery Analysis
        'sl_then_recovered': t.sl_then_recovered,
        'post_sl_max_price': t.post_sl_max_price,
        'post_sl_max_gain_pct': t.post_sl_max_gain_pct,
        'post_sl_fib_levels': t.post_sl_fib_levels or {},
        'post_sl_monitoring_hours': t.post_sl_monitoring_hours,
        'post_sl_would_have_won': t.post_sl_would_have_won,
        # V3 Golden Box
        'strategy_version': getattr(t, 'strategy_version', 'v1'),
        'v3_box_high': getattr(t, 'v3_box_high', None),
        'v3_box_low': getattr(t, 'v3_box_low', None),
        'v3_hours_to_entry': getattr(t, 'v3_hours_to_entry', None),
        'v3_sl_distance_pct': getattr(t, 'v3_sl_distance_pct', None),
        'v3_quality_score': int.from_bytes(t.v3_quality_score, 'little') if isinstance(getattr(t, 'v3_quality_score', None), bytes) else getattr(t, 'v3_quality_score', None),
        'v3_breakout_dt': t.v3_breakout_dt.isoformat() if getattr(t, 'v3_breakout_dt', None) else None,
        'v3_breakout_high': getattr(t, 'v3_breakout_high', None),
        'v3_retest_datetime': t.v3_retest_datetime.isoformat() if getattr(t, 'v3_retest_datetime', None) else None,
        'v3_retest_price': getattr(t, 'v3_retest_price', None),
        'v3_prog_count': int.from_bytes(t.v3_prog_count, 'little') if isinstance(getattr(t, 'v3_prog_count', None), bytes) else getattr(t, 'v3_prog_count', None),
        # MEGA BUY Details from linked alert
        'mega_buy_details': alerts_map.get(t.alert_id).mega_buy_details if t.alert_id and alerts_map.get(t.alert_id) else {}
    })

db.close()
print(json.dumps(result))
`

    const output = await runPython(script)
    const trades = JSON.parse(output.trim())
    return NextResponse.json({ trades })
  } catch (error) {
    console.error("Error fetching trades:", error)
    return NextResponse.json({ error: String(error), trades: [] }, { status: 500 })
  }
}
