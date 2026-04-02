import { NextRequest, NextResponse } from "next/server"

const BACKTEST_API = "http://localhost:9001"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const path = searchParams.get("path")

    // If path=alerts — fetch all alerts + trades from all backtests
    if (path === "alerts") {
      const btRes = await fetch(`${BACKTEST_API}/api/backtests?limit=500`, { cache: "no-store" })
      const backtests = btRes.ok ? await btRes.json() : []
      if (!Array.isArray(backtests)) return NextResponse.json({ alerts: [], trades: [] })

      const withAlerts = backtests.filter((b: any) => b.total_alerts > 0)
      const withTrades = backtests.filter((b: any) => b.total_trades > 0)
      const allAlerts: any[] = []
      const allTrades: any[] = []

      // Batch fetch alerts
      for (let i = 0; i < withAlerts.length; i += 20) {
        const batch = withAlerts.slice(i, i + 20)
        const results = await Promise.allSettled(
          batch.map((bt: any) =>
            fetch(`${BACKTEST_API}/api/backtests/${bt.id}/alerts`, { cache: "no-store" })
              .then(r => r.ok ? r.json() : [])
              .then(alerts => (Array.isArray(alerts) ? alerts : []).map((a: any) => ({ ...a, symbol: bt.symbol, backtest_id: bt.id })))
          )
        )
        results.forEach(r => { if (r.status === "fulfilled") allAlerts.push(...r.value) })
      }

      // Batch fetch trades
      for (let i = 0; i < withTrades.length; i += 20) {
        const batch = withTrades.slice(i, i + 20)
        const results = await Promise.allSettled(
          batch.map((bt: any) =>
            fetch(`${BACKTEST_API}/api/backtests/${bt.id}/trades`, { cache: "no-store" })
              .then(r => r.ok ? r.json() : [])
              .then(trades => (Array.isArray(trades) ? trades : []).map((t: any) => ({ ...t, symbol: bt.symbol, backtest_id: bt.id })))
          )
        )
        results.forEach(r => { if (r.status === "fulfilled") allTrades.push(...r.value) })
      }

      return NextResponse.json({ alerts: allAlerts, trades: allTrades })
    }

    // Default: fetch backtests + stats
    const limit = searchParams.get("limit") || "500"
    const [backtestsRes, statsRes] = await Promise.allSettled([
      fetch(`${BACKTEST_API}/api/backtests?limit=${limit}`, { cache: "no-store" }),
      fetch(`${BACKTEST_API}/api/stats`, { cache: "no-store" })
    ])

    const backtests = backtestsRes.status === "fulfilled" && backtestsRes.value.ok
      ? await backtestsRes.value.json()
      : []

    const stats = statsRes.status === "fulfilled" && statsRes.value.ok
      ? await statsRes.value.json()
      : null

    return NextResponse.json({ backtests, stats })
  } catch (error) {
    console.error("Error proxying to backtest API:", error)
    return NextResponse.json({ error: String(error), backtests: [], stats: null }, { status: 500 })
  }
}
