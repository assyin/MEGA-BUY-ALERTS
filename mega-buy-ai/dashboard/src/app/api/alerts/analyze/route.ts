import { NextRequest, NextResponse } from "next/server"
import { spawn } from "child_process"
import path from "path"

// Allow up to 60s for this endpoint (Python fetches 9 Binance kline sets)
export const maxDuration = 60
export const dynamic = 'force-dynamic'

const BACKTEST_DIR = path.join(process.cwd(), "..", "backtest")
const PYTHON_PATH = path.join(BACKTEST_DIR, "venv", "bin", "python")

async function runPython(script: string, timeoutMs: number = 30000): Promise<string> {
  return new Promise((resolve, reject) => {
    // Try venv python first, fallback to system python
    const pythonPaths = [PYTHON_PATH, "python3", "python"]
    let proc: ReturnType<typeof spawn> | null = null

    function tryNext(paths: string[]) {
      if (paths.length === 0) {
        reject(new Error("No Python interpreter found"))
        return
      }
      const pyPath = paths[0]
      proc = spawn(pyPath, ["-c", script], { cwd: BACKTEST_DIR })

      let stdout = ""
      let stderr = ""

      const timer = setTimeout(() => {
        proc?.kill()
        reject(new Error(`Python process timed out after ${timeoutMs}ms`))
      }, timeoutMs)

      proc.stdout.on("data", (data) => { stdout += data.toString() })
      proc.stderr.on("data", (data) => { stderr += data.toString() })

      proc.on("error", () => {
        clearTimeout(timer)
        tryNext(paths.slice(1))
      })

      proc.on("close", (code) => {
        clearTimeout(timer)
        if (code === 0) {
          resolve(stdout)
        } else {
          reject(new Error(stderr || `Process exited with code ${code}`))
        }
      })
    }

    tryNext(pythonPaths)
  })
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const pair = searchParams.get("pair")
    const timestamp = searchParams.get("timestamp") || ""
    const price = parseFloat(searchParams.get("price") || "0") || 0

    if (!pair) {
      return NextResponse.json({ error: "Missing pair parameter" }, { status: 400 })
    }

    // Sanitize inputs
    const safePair = pair.replace(/[^A-Za-z0-9]/g, "").toUpperCase()
    const safeTs = timestamp.replace(/[^0-9T:Z+\-.]/g, "")

    const script = `
import json
import sys
sys.path.insert(0, '.')
from api.realtime_analyze import analyze_alert_realtime
result = analyze_alert_realtime("${safePair}", "${safeTs}", ${price})
print(json.dumps(result))
`

    const output = await runPython(script, 30000)

    // Find the JSON in stdout (skip any warnings/logs)
    const jsonStart = output.indexOf('{')
    if (jsonStart === -1) {
      return NextResponse.json({ error: "No JSON output from Python" }, { status: 500 })
    }

    const jsonStr = output.substring(jsonStart)
    const data = JSON.parse(jsonStr)
    return NextResponse.json(data)

  } catch (error) {
    console.error("Alert analysis error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Analysis failed" },
      { status: 500 }
    )
  }
}
