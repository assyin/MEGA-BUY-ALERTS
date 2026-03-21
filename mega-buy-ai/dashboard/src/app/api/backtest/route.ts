import { NextRequest, NextResponse } from "next/server"
import { spawn } from "child_process"
import path from "path"

const BACKTEST_DIR = path.join(process.cwd(), "..", "backtest")
const PYTHON_PATH = path.join(BACKTEST_DIR, "venv", "bin", "python")
const DB_PATH = path.join(BACKTEST_DIR, "data", "backtest.db")

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
    const script = `
import json
import sys
sys.path.insert(0, '.')
from api.models import SessionLocal, BacktestRun

db = SessionLocal()
runs = db.query(BacktestRun).order_by(BacktestRun.created_at.desc()).all()

result = []
for run in runs:
    result.append({
        'id': run.id,
        'symbol': run.symbol,
        'start_date': run.start_date.isoformat() if run.start_date else None,
        'end_date': run.end_date.isoformat() if run.end_date else None,
        'total_alerts': run.total_alerts,
        'stc_validated': run.stc_validated,
        'rejected_15m_alone': run.rejected_15m_alone,
        'valid_combos': run.valid_combos,
        'with_tl_break': run.with_tl_break,
        'delay_respected': run.delay_respected,
        'delay_exceeded': run.delay_exceeded,
        'expired': run.expired,
        'waiting': run.waiting,
        'valid_entries': run.valid_entries,
        'no_entry': run.no_entry,
        'total_trades': run.total_trades,
        'pnl_strategy_c': run.pnl_strategy_c,
        'pnl_strategy_d': run.pnl_strategy_d,
        'avg_pnl_c': run.avg_pnl_c,
        'avg_pnl_d': run.avg_pnl_d,
        'created_at': run.created_at.isoformat() if run.created_at else None,
        'strategy_version': getattr(run, 'strategy_version', 'v1'),
        'v2_rejected_count': getattr(run, 'v2_rejected_count', 0),
        'v2_rejection_reasons': getattr(run, 'v2_rejection_reasons', {})
    })

db.close()
print(json.dumps(result))
`

    const output = await runPython(script)
    const backtests = JSON.parse(output.trim())
    return NextResponse.json({ backtests })
  } catch (error) {
    console.error("Error fetching backtests:", error)
    return NextResponse.json({ error: String(error), backtests: [] }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { symbol, start_date, end_date, strategy_version = 'v1' } = body

    if (!symbol || !start_date || !end_date) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 })
    }

    const script = `
import json
import sys
sys.path.insert(0, '.')
from api.engine import BacktestEngine
from api.models import SessionLocal, BacktestRun

engine = BacktestEngine()

def progress(msg):
    pass  # Silent mode

run_id = engine.run_backtest("${symbol}", "${start_date}", "${end_date}", progress, strategy_version="${strategy_version}")

db = SessionLocal()
run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()

result = {
    'id': run.id,
    'symbol': run.symbol,
    'trades': run.total_trades,
    'alerts': run.total_alerts,
    'pnl_c': run.pnl_strategy_c,
    'pnl_d': run.pnl_strategy_d,
    'strategy_version': run.strategy_version,
    'v2_rejected_count': run.v2_rejected_count
}

db.close()
print(json.dumps(result))
`

    const output = await runPython(script)
    const result = JSON.parse(output.trim())
    return NextResponse.json(result)
  } catch (error) {
    console.error("Error running backtest:", error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function DELETE(request: NextRequest) {
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
from api.models import SessionLocal, BacktestRun, Alert, Trade

db = SessionLocal()
db.query(Trade).filter(Trade.backtest_run_id == ${id}).delete()
db.query(Alert).filter(Alert.backtest_run_id == ${id}).delete()
db.query(BacktestRun).filter(BacktestRun.id == ${id}).delete()
db.commit()
db.close()
print(json.dumps({'success': True}))
`

    const output = await runPython(script)
    return NextResponse.json(JSON.parse(output.trim()))
  } catch (error) {
    console.error("Error deleting backtest:", error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
