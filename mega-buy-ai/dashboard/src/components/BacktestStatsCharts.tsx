"use client"

import { useState, useEffect, useMemo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  ComposedChart,
  Line,
  Area,
} from "recharts"
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Trophy,
  Skull,
  AlertTriangle,
  RefreshCw,
  Percent,
  Layers,
  Filter as FilterIcon,
  Zap,
} from "lucide-react"

interface BacktestData {
  id: number
  symbol: string
  start_date: string
  end_date: string
  created_at: string
  strategy_version: string
  total_alerts: number
  stc_validated: number
  valid_combos: number
  valid_entries: number
  total_trades: number
  pnl_strategy_c: number
  pnl_strategy_d: number
  avg_pnl_c: number
  avg_pnl_d: number
  rejected_15m_alone?: number
  with_tl_break?: number
  delay_respected?: number
  delay_exceeded?: number
  expired?: number
  waiting?: number
  no_entry?: number
}

const COLORS = {
  green: "#4ade80",
  red: "#f87171",
  purple: "#a78bfa",
  cyan: "#22d3ee",
  amber: "#fbbf24",
  pink: "#f472b6",
  emerald: "#34d399",
  orange: "#fb923c",
  grid: "#374151",
  text: "#9ca3af",
  bg: "rgba(17, 24, 39, 0.6)",
}

const TODAY = new Date().toISOString().slice(0, 10)

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      {payload.map((entry, idx) => (
        <p key={idx} className="text-sm font-medium" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === "number" ? entry.value.toFixed(2) : entry.value}
        </p>
      ))}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex items-center justify-center h-full text-gray-500 text-sm">
      Pas assez de donnees
    </div>
  )
}

interface BacktestStatsChartsProps {
  backtests: BacktestData[]
}

export default function BacktestStatsCharts({ backtests }: BacktestStatsChartsProps) {
  // ─── Filters ───────────────────────────────────────────
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [symbolFilter, setSymbolFilter] = useState("")
  const [minAlerts, setMinAlerts] = useState("")
  const [minTrades, setMinTrades] = useState("")

  // Apply filters — backtest is included if its period OVERLAPS with filter range
  const data = useMemo(() => {
    return backtests.filter(bt => {
      // Date overlap: backtest [start, end] must overlap with [dateFrom, dateTo]
      if (dateFrom && bt.end_date && (bt.end_date || "").slice(0, 10) < dateFrom) return false
      if (dateTo && bt.start_date && (bt.start_date || "").slice(0, 10) > dateTo) return false
      if (symbolFilter && !bt.symbol.toLowerCase().includes(symbolFilter.toLowerCase())) return false
      if (minAlerts && bt.total_alerts < parseInt(minAlerts)) return false
      if (minTrades && bt.total_trades < parseInt(minTrades)) return false
      return true
    })
  }, [backtests, dateFrom, dateTo, symbolFilter, minAlerts, minTrades])

  // ─── Load individual alerts + trades for daily stats ─────
  const [alerts, setAlerts] = useState<any[]>([])
  const [trades, setTrades] = useState<any[]>([])
  const [loadingAlerts, setLoadingAlerts] = useState(false)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  const handleChartClick = (data: any) => {
    if (data?.activePayload?.[0]?.payload?.fullDate) {
      setSelectedDay(data.activePayload[0].payload.fullDate)
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoadingAlerts(true)
      try {
        const res = await fetch('/api/backtest/stats?path=alerts')
        if (res.ok) {
          const result = await res.json()
          if (result.alerts) setAlerts(result.alerts)
          if (result.trades) setTrades(result.trades)
        }
      } catch (e) {
        console.error('Failed to load backtest alerts:', e)
      }
      setLoadingAlerts(false)
    }
    loadData()
  }, [])

  // ─── Daily Stats based on ALERT + TRADE DATES ─────────
  const dailyStats = useMemo(() => {
    if (alerts.length === 0 && trades.length === 0) return []

    // Calculate scanned pairs per day from backtests (pairs whose period covers that day)
    const scannedByDay: Record<string, number> = {}
    data.forEach(bt => {
      const btStart = (bt.start_date || "").slice(0, 10)
      const btEnd = (bt.end_date || "").slice(0, 10)
      if (!btStart || !btEnd) return
      const s = new Date(btStart)
      const e = new Date(btEnd)
      for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
        const key = d.toISOString().slice(0, 10)
        scannedByDay[key] = (scannedByDay[key] || 0) + 1
      }
    })

    // Filter alerts by date range
    const filteredAlerts = alerts.filter(a => {
      const d = (a.alert_datetime || "").slice(0, 10)
      if (!d) return false
      if (dateFrom && d < dateFrom) return false
      if (dateTo && d > dateTo) return false
      if (symbolFilter && !(a.symbol || "").toLowerCase().includes(symbolFilter.toLowerCase())) return false
      return true
    })

    // Filter trades by alert_datetime
    const filteredTrades = trades.filter(t => {
      const d = (t.alert_datetime || "").slice(0, 10)
      if (!d) return false
      if (dateFrom && d < dateFrom) return false
      if (dateTo && d > dateTo) return false
      if (symbolFilter && !(t.symbol || "").toLowerCase().includes(symbolFilter.toLowerCase())) return false
      return true
    })

    // Get date range
    const allDates = [
      ...filteredAlerts.map(a => (a.alert_datetime || "").slice(0, 10)),
      ...filteredTrades.map(t => (t.alert_datetime || "").slice(0, 10)),
    ].filter(Boolean)
    if (allDates.length === 0) return []

    const sortedDates = [...allDates].sort()
    const minDate = sortedDates[0]
    const maxDate = sortedDates[sortedDates.length - 1]

    // Init all days
    const byDay: Record<string, { alerts: number; trades: number; wins: number; losses: number; pnl: number; pairs: Set<string> }> = {}
    const startD = new Date(minDate)
    const endD = new Date(maxDate)
    for (let d = new Date(startD); d <= endD; d.setDate(d.getDate() + 1)) {
      byDay[d.toISOString().slice(0, 10)] = { alerts: 0, trades: 0, wins: 0, losses: 0, pnl: 0, pairs: new Set() }
    }

    // Fill alerts count by alert_datetime + track unique pairs
    filteredAlerts.forEach(alert => {
      const day = (alert.alert_datetime || "").slice(0, 10)
      if (byDay[day]) {
        byDay[day].alerts += 1
        if (alert.symbol) byDay[day].pairs.add(alert.symbol)
      }
    })

    // Fill trades by alert_datetime (PnL comes from trades, not alerts)
    filteredTrades.forEach(trade => {
      const day = (trade.alert_datetime || "").slice(0, 10)
      if (!byDay[day]) return
      byDay[day].trades += 1
      if (trade.symbol) byDay[day].pairs.add(trade.symbol)
      const pnl = trade.pnl_c || 0
      byDay[day].pnl += pnl
      if (pnl > 0) byDay[day].wins += 1
      else byDay[day].losses += 1
    })

    const sorted = Object.entries(byDay).sort(([a], [b]) => a.localeCompare(b))
    let cumPnl = 0
    return sorted.map(([date, s]) => {
      cumPnl += s.pnl
      return {
        date: `${date.slice(8, 10)}/${date.slice(5, 7)}`,
        fullDate: date,
        scanned: scannedByDay[date] || 0,
        alerts: s.alerts,
        pairs: s.pairs.size,
        trades: s.trades,
        wins: s.wins,
        losses: s.losses,
        wr: s.trades > 0 ? Math.round(s.wins / s.trades * 100) : null,
        pnl: Math.round(s.pnl * 100) / 100,
        cumPnl: Math.round(cumPnl * 100) / 100,
      }
    })
  }, [alerts, trades, dateFrom, dateTo, symbolFilter])

  // --- Global Stats ---
  const globalStats = useMemo(() => {
    if (data.length === 0) return null

    const totalBacktests = data.length
    const uniqueSymbols = new Set(data.map((d) => d.symbol)).size
    const totalAlerts = data.reduce((s, d) => s + (d.total_alerts || 0), 0)
    const totalValidated = data.reduce((s, d) => s + (d.valid_entries || 0), 0)
    const totalTrades = data.reduce((s, d) => s + (d.total_trades || 0), 0)

    const withTrades = data.filter((d) => d.total_trades > 0)
    const avgPnl = withTrades.length > 0
      ? withTrades.reduce((s, d) => s + d.pnl_strategy_c, 0) / withTrades.length
      : 0
    const wins = withTrades.filter((d) => d.pnl_strategy_c > 0).length
    const winRate = withTrades.length > 0 ? (wins / withTrades.length) * 100 : 0

    // Best pair by total PnL
    const bySymbol: Record<string, number> = {}
    data.forEach((d) => {
      bySymbol[d.symbol] = (bySymbol[d.symbol] || 0) + d.pnl_strategy_c
    })
    const bestPair = Object.entries(bySymbol).sort((a, b) => b[1] - a[1])[0]

    return { totalBacktests, uniqueSymbols, totalAlerts, totalValidated, totalTrades, avgPnl, winRate, bestPair }
  }, [data])

  // --- PnL Distribution ---
  const pnlDistribution = useMemo(() => {
    const withTrades = data.filter((d) => d.total_trades > 0)
    if (withTrades.length === 0) return []

    const ranges = [
      { label: "< -50%", min: -Infinity, max: -50 },
      { label: "-50 a -20%", min: -50, max: -20 },
      { label: "-20 a -10%", min: -20, max: -10 },
      { label: "-10 a 0%", min: -10, max: 0 },
      { label: "0 a 10%", min: 0, max: 10 },
      { label: "10 a 20%", min: 10, max: 20 },
      { label: "20 a 50%", min: 20, max: 50 },
      { label: "> 50%", min: 50, max: Infinity },
    ]

    return ranges.map((r) => ({
      range: r.label,
      count: withTrades.filter(
        (d) => d.pnl_strategy_c >= r.min && d.pnl_strategy_c < r.max
      ).length,
      isPositive: r.min >= 0,
    }))
  }, [data])

  // --- Top 20 Pairs by PnL ---
  const top20Pairs = useMemo(() => {
    const bySymbol: Record<string, { pnl: number; count: number }> = {}
    data.forEach((d) => {
      if (!bySymbol[d.symbol]) bySymbol[d.symbol] = { pnl: 0, count: 0 }
      bySymbol[d.symbol].pnl += d.pnl_strategy_c
      bySymbol[d.symbol].count++
    })
    return Object.entries(bySymbol)
      .filter(([, v]) => v.pnl !== 0)
      .sort((a, b) => b[1].pnl - a[1].pnl)
      .slice(0, 20)
      .map(([symbol, v]) => ({ symbol: symbol.replace("USDT", ""), pnl: parseFloat(v.pnl.toFixed(2)), count: v.count }))
  }, [data])

  // --- Worst 20 Pairs ---
  const worst20Pairs = useMemo(() => {
    const bySymbol: Record<string, { pnl: number; count: number }> = {}
    data.forEach((d) => {
      if (!bySymbol[d.symbol]) bySymbol[d.symbol] = { pnl: 0, count: 0 }
      bySymbol[d.symbol].pnl += d.pnl_strategy_c
      bySymbol[d.symbol].count++
    })
    return Object.entries(bySymbol)
      .filter(([, v]) => v.pnl !== 0)
      .sort((a, b) => a[1].pnl - b[1].pnl)
      .slice(0, 20)
      .map(([symbol, v]) => ({ symbol: symbol.replace("USDT", ""), pnl: parseFloat(v.pnl.toFixed(2)), count: v.count }))
  }, [data])

  // --- Win Rate Distribution ---
  const winRateDistribution = useMemo(() => {
    const bySymbol: Record<string, { wins: number; total: number }> = {}
    data.filter((d) => d.total_trades > 0).forEach((d) => {
      if (!bySymbol[d.symbol]) bySymbol[d.symbol] = { wins: 0, total: 0 }
      bySymbol[d.symbol].total++
      if (d.pnl_strategy_c > 0) bySymbol[d.symbol].wins++
    })

    const ranges = [
      { label: "0%", min: 0, max: 0.001 },
      { label: "1-25%", min: 0.001, max: 25 },
      { label: "25-50%", min: 25, max: 50 },
      { label: "50-75%", min: 50, max: 75 },
      { label: "75-99%", min: 75, max: 100 },
      { label: "100%", min: 100, max: 100.001 },
    ]

    const symbols = Object.entries(bySymbol).map(([, v]) => (v.wins / v.total) * 100)

    return ranges.map((r) => ({
      range: r.label,
      count: symbols.filter((wr) => wr >= r.min && wr < r.max).length,
    }))
  }, [data])

  // --- Alerts vs Validated (top 20 by alert count) ---
  const alertsVsValidated = useMemo(() => {
    const bySymbol: Record<string, { alerts: number; entries: number }> = {}
    data.forEach((d) => {
      if (!bySymbol[d.symbol]) bySymbol[d.symbol] = { alerts: 0, entries: 0 }
      bySymbol[d.symbol].alerts += d.total_alerts || 0
      bySymbol[d.symbol].entries += d.valid_entries || 0
    })
    return Object.entries(bySymbol)
      .sort((a, b) => b[1].alerts - a[1].alerts)
      .slice(0, 20)
      .map(([symbol, v]) => ({
        symbol: symbol.replace("USDT", ""),
        alerts: v.alerts,
        entries: v.entries,
        rate: v.alerts > 0 ? ((v.entries / v.alerts) * 100).toFixed(0) : "0",
      }))
  }, [data])

  // --- Backtest by Date (last 30 days) ---
  const backtestsByDate = useMemo(() => {
    const counts: Record<string, number> = {}
    data.forEach((d) => {
      if (d.created_at) {
        const date = d.created_at.slice(0, 10)
        counts[date] = (counts[date] || 0) + 1
      }
    })

    // Generate last 30 days
    const result = []
    for (let i = 29; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const dateStr = d.toISOString().slice(0, 10)
      const isToday = dateStr === TODAY
      result.push({
        date: dateStr.slice(5) + (isToday ? " (auj)" : ""),
        count: counts[dateStr] || 0,
      })
    }
    return result
  }, [data])

  // --- Average PnL by Day of Week ---
  const pnlByDayOfWeek = useMemo(() => {
    const days = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]
    const dayData: Record<number, { total: number; count: number }> = {}

    data.filter((d) => d.total_trades > 0 && d.created_at).forEach((d) => {
      const dayIdx = new Date(d.created_at).getDay()
      if (!dayData[dayIdx]) dayData[dayIdx] = { total: 0, count: 0 }
      dayData[dayIdx].total += d.pnl_strategy_c
      dayData[dayIdx].count++
    })

    return days.map((name, idx) => ({
      day: name,
      avgPnl: dayData[idx] ? parseFloat((dayData[idx].total / dayData[idx].count).toFixed(2)) : 0,
      count: dayData[idx]?.count || 0,
    }))
  }, [data])

  // --- Strategy Funnel ---
  const strategyFunnel = useMemo(() => {
    const totalAlerts = data.reduce((s, d) => s + (d.total_alerts || 0), 0)
    const stcValidated = data.reduce((s, d) => s + (d.stc_validated || 0), 0)
    const validCombos = data.reduce((s, d) => s + (d.valid_combos || 0), 0)
    const validEntries = data.reduce((s, d) => s + (d.valid_entries || 0), 0)
    const totalTrades = data.reduce((s, d) => s + (d.total_trades || 0), 0)

    return [
      { step: "Alertes", value: totalAlerts, color: COLORS.purple },
      { step: "STC Valid", value: stcValidated, color: COLORS.cyan },
      { step: "Combos", value: validCombos, color: COLORS.amber },
      { step: "Entries", value: validEntries, color: COLORS.green },
      { step: "Trades", value: totalTrades, color: COLORS.emerald },
    ]
  }, [data])

  // --- PnL vs Number of Trades (Scatter) ---
  const pnlScatter = useMemo(() => {
    const bySymbol: Record<string, { trades: number; pnl: number }> = {}
    data.forEach((d) => {
      if (!bySymbol[d.symbol]) bySymbol[d.symbol] = { trades: 0, pnl: 0 }
      bySymbol[d.symbol].trades += d.total_trades
      bySymbol[d.symbol].pnl += d.pnl_strategy_c
    })
    return Object.entries(bySymbol)
      .filter(([, v]) => v.trades > 0)
      .map(([symbol, v]) => ({
        symbol: symbol.replace("USDT", ""),
        trades: v.trades,
        avgPnl: parseFloat((v.pnl / v.trades).toFixed(2)),
      }))
  }, [data])

  if (data.length === 0) {
    return (
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-12 text-center">
        <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400 text-lg">Pas assez de donnees</p>
        <p className="text-gray-500 text-sm mt-1">Lancez des backtests pour voir les statistiques</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ═══ FILTERS ═══ */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Filtres</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label className="text-xs text-gray-500">Date debut</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
              className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 focus:outline-none focus:border-purple-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Date fin</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
              className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 focus:outline-none focus:border-purple-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Paire</label>
            <input type="text" placeholder="BTC, SOL..." value={symbolFilter} onChange={e => setSymbolFilter(e.target.value)}
              className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Min alertes</label>
            <input type="number" placeholder="0" value={minAlerts} onChange={e => setMinAlerts(e.target.value)}
              className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Min trades</label>
            <input type="number" placeholder="0" value={minTrades} onChange={e => setMinTrades(e.target.value)}
              className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
          </div>
        </div>
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-500">
            {data.length} / {backtests.length} backtests | {alerts.length} alertes | {trades.length} trades
            {loadingAlerts && " (chargement...)"}
          </span>
          <button onClick={() => { setDateFrom(""); setDateTo(""); setSymbolFilter(""); setMinAlerts(""); setMinTrades("") }}
            className="text-xs text-gray-400 hover:text-gray-200">Reset filtres</button>
        </div>
      </div>

      {/* ═══ DAY DETAIL MODAL ═══ */}
      {selectedDay && (
        <DayDetailModal
          date={selectedDay}
          alerts={alerts.filter(a => (a.alert_datetime || "").slice(0, 10) === selectedDay)}
          trades={trades.filter(t => (t.alert_datetime || "").slice(0, 10) === selectedDay)}
          onClose={() => setSelectedDay(null)}
        />
      )}

      {/* ═══ DAILY COMBINED CHARTS ═══ */}
      <h2 className="text-lg font-bold text-gray-200">📅 Statistiques par Jour (date alerte MEGA BUY) — cliquez sur un jour pour voir les details</h2>
      <div className="space-y-4">

        {/* Chart 1: Activite & Performance — alertes, wins, losses (barres) + WR% (ligne) */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-1">Activite & Performance / Jour</h3>
          <p className="text-xs text-gray-500 mb-3">Barres: scannees (gris), alertes (jaune), paires avec alerte (violet), trades win (vert), trades lose (rouge) | Ligne: Win Rate %</p>
          {loadingAlerts ? (
            <div className="flex items-center justify-center h-[320px] text-gray-500 text-sm">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500 mr-3" />
              Chargement des alertes...
            </div>
          ) : dailyStats.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={dailyStats} onClick={handleChartClick} style={{ cursor: 'pointer' }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={Math.max(0, Math.floor(dailyStats.length / 15))} angle={-45} textAnchor="end" height={50} />
                <YAxis yAxisId="left" tick={{ fontSize: 10, fill: COLORS.text }} allowDecimals={false} label={{ value: 'Nombre', angle: -90, position: 'insideLeft', fill: COLORS.text, fontSize: 10 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: COLORS.cyan }} domain={[0, 100]} label={{ value: 'WR %', angle: 90, position: 'insideRight', fill: COLORS.cyan, fontSize: 10 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: COLORS.text }} />
                {/* Barres empilees: alertes en fond, wins + losses au premier plan */}
                <Bar yAxisId="left" dataKey="scanned" name="Paires scannees" fill={COLORS.text} opacity={0.12} radius={[2, 2, 0, 0]} />
                <Bar yAxisId="left" dataKey="alerts" name="Alertes" fill={COLORS.amber} opacity={0.3} radius={[2, 2, 0, 0]} />
                <Bar yAxisId="left" dataKey="pairs" name="Paires avec alerte" fill={COLORS.purple} opacity={0.4} radius={[2, 2, 0, 0]} />
                <Bar yAxisId="left" dataKey="wins" name="Trades WIN" stackId="trades" fill={COLORS.green} radius={[0, 0, 0, 0]} />
                <Bar yAxisId="left" dataKey="losses" name="Trades LOSE" stackId="trades" fill={COLORS.red} radius={[2, 2, 0, 0]} />
                {/* Ligne WR sur l'axe droit */}
                <Line yAxisId="right" type="monotone" dataKey="wr" name="Win Rate %" stroke={COLORS.cyan} strokeWidth={2} dot={{ r: 2, fill: COLORS.cyan }} connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          ) : <EmptyState />}
          {/* Day selector buttons */}
          {dailyStats.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {dailyStats.filter(d => d.alerts > 0 || d.trades > 0).map(d => (
                <button
                  key={d.fullDate}
                  onClick={() => setSelectedDay(d.fullDate)}
                  className={`px-2 py-1 text-[10px] rounded border transition-colors ${
                    d.trades > 0
                      ? (d.wr || 0) >= 60
                        ? 'bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20'
                        : (d.wr || 0) >= 40
                          ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/20'
                          : 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                      : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                  }`}
                  title={`${d.alerts} alertes, ${d.trades} trades, WR ${d.wr || 0}%, PnL ${d.pnl >= 0 ? '+' : ''}${d.pnl}%`}
                >
                  {d.date} {d.scanned}sc/{d.pairs}p/{d.alerts}a/{d.trades}t{d.trades > 0 ? ` WR${d.wr}% ${d.pnl >= 0 ? '+' : ''}${d.pnl}%` : ''}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Chart 2: PnL journalier (barres) + PnL cumule (ligne area) */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-1">PnL / Jour</h3>
          <p className="text-xs text-gray-500 mb-3">Barres: PnL journalier (vert/rouge) | Ligne: PnL cumule</p>
          {loadingAlerts ? (
            <div className="flex items-center justify-center h-[320px] text-gray-500 text-sm">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500 mr-3" />
              Chargement des trades...
            </div>
          ) : dailyStats.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={dailyStats} onClick={handleChartClick} style={{ cursor: 'pointer' }}>
                <defs>
                  <linearGradient id="cumPnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.purple} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS.purple} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={Math.max(0, Math.floor(dailyStats.length / 15))} angle={-45} textAnchor="end" height={50} />
                <YAxis yAxisId="left" tick={{ fontSize: 10, fill: COLORS.text }} label={{ value: 'PnL %', angle: -90, position: 'insideLeft', fill: COLORS.text, fontSize: 10 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: COLORS.purple }} label={{ value: 'Cumule %', angle: 90, position: 'insideRight', fill: COLORS.purple, fontSize: 10 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: COLORS.text }} />
                {/* Barres PnL journalier */}
                <Bar yAxisId="left" dataKey="pnl" name="PnL Jour %" radius={[3, 3, 0, 0]}>
                  {dailyStats.map((entry, i) => (
                    <Cell key={i} fill={entry.pnl >= 0 ? COLORS.green : COLORS.red} />
                  ))}
                </Bar>
                {/* Area PnL cumule */}
                <Area yAxisId="right" type="monotone" dataKey="cumPnl" name="PnL Cumule %" stroke={COLORS.purple} fill="url(#cumPnlGrad)" strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : <EmptyState />}
        </div>

      </div>

      <h2 className="text-lg font-bold text-gray-200 mt-4">📊 Statistiques Globales</h2>

      {/* Global Stats Cards */}
      {globalStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
          <StatCard label="Backtests" value={globalStats.totalBacktests} icon={<BarChart3 className="w-4 h-4" />} color="text-purple-400" />
          <StatCard label="Symbols" value={globalStats.uniqueSymbols} icon={<Layers className="w-4 h-4" />} color="text-cyan-400" />
          <StatCard label="Alertes" value={globalStats.totalAlerts} icon={<Zap className="w-4 h-4" />} color="text-amber-400" />
          <StatCard label="Validees" value={globalStats.totalValidated} icon={<Target className="w-4 h-4" />} color="text-green-400" />
          <StatCard label="Trades" value={globalStats.totalTrades} icon={<Activity className="w-4 h-4" />} color="text-pink-400" />
          <StatCard
            label="Moy PnL"
            value={`${globalStats.avgPnl >= 0 ? "+" : ""}${globalStats.avgPnl.toFixed(1)}%`}
            icon={<TrendingUp className="w-4 h-4" />}
            color={globalStats.avgPnl >= 0 ? "text-green-400" : "text-red-400"}
          />
          <StatCard
            label="Win Rate"
            value={`${globalStats.winRate.toFixed(1)}%`}
            icon={<Trophy className="w-4 h-4" />}
            color={globalStats.winRate >= 50 ? "text-green-400" : "text-red-400"}
          />
          <StatCard
            label="Best Pair"
            value={globalStats.bestPair ? globalStats.bestPair[0].replace("USDT", "") : "-"}
            subValue={globalStats.bestPair ? `+${globalStats.bestPair[1].toFixed(1)}%` : ""}
            icon={<Trophy className="w-4 h-4" />}
            color="text-yellow-400"
          />
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. PnL Distribution */}
        <ChartCard title="Distribution PnL" icon={<BarChart3 className="w-4 h-4 text-purple-400" />}>
          {pnlDistribution.length === 0 ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={pnlDistribution} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="range" tick={{ fill: COLORS.text, fontSize: 11 }} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Backtests" radius={[4, 4, 0, 0]}>
                  {pnlDistribution.map((entry, idx) => (
                    <Cell key={idx} fill={entry.isPositive ? COLORS.green : COLORS.red} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 2. Strategy Funnel */}
        <ChartCard title="Entonnoir Strategie" icon={<FilterIcon className="w-4 h-4 text-cyan-400" />}>
          {strategyFunnel.every((s) => s.value === 0) ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={strategyFunnel} layout="vertical" margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis type="number" tick={{ fill: COLORS.text, fontSize: 11 }} />
                <YAxis type="category" dataKey="step" tick={{ fill: COLORS.text, fontSize: 12 }} width={80} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="value" name="Total" radius={[0, 4, 4, 0]}>
                  {strategyFunnel.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 3. Top 20 Pairs */}
        <ChartCard title="Top 20 Pairs (PnL)" icon={<TrendingUp className="w-4 h-4 text-green-400" />}>
          {top20Pairs.length === 0 ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(280, top20Pairs.length * 24)}>
              <BarChart data={top20Pairs} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis type="number" tick={{ fill: COLORS.text, fontSize: 11 }} />
                <YAxis type="category" dataKey="symbol" tick={{ fill: COLORS.text, fontSize: 11 }} width={70} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="pnl" name="PnL %" radius={[0, 4, 4, 0]}>
                  {top20Pairs.map((entry, idx) => (
                    <Cell key={idx} fill={entry.pnl >= 0 ? COLORS.green : COLORS.red} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 4. Worst 20 Pairs */}
        <ChartCard title="Worst 20 Pairs (PnL)" icon={<TrendingDown className="w-4 h-4 text-red-400" />}>
          {worst20Pairs.length === 0 ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(280, worst20Pairs.length * 24)}>
              <BarChart data={worst20Pairs} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis type="number" tick={{ fill: COLORS.text, fontSize: 11 }} />
                <YAxis type="category" dataKey="symbol" tick={{ fill: COLORS.text, fontSize: 11 }} width={70} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="pnl" name="PnL %" radius={[0, 4, 4, 0]}>
                  {worst20Pairs.map((entry, idx) => (
                    <Cell key={idx} fill={entry.pnl >= 0 ? COLORS.green : COLORS.red} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 5. Win Rate Distribution */}
        <ChartCard title="Distribution Win Rate" icon={<Trophy className="w-4 h-4 text-amber-400" />}>
          {winRateDistribution.every((d) => d.count === 0) ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={winRateDistribution} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="range" tick={{ fill: COLORS.text, fontSize: 11 }} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Pairs" fill={COLORS.amber} radius={[4, 4, 0, 0]} fillOpacity={0.8} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 6. Alerts vs Validated */}
        <ChartCard title="Alertes vs Entries validees" icon={<Target className="w-4 h-4 text-purple-400" />}>
          {alertsVsValidated.length === 0 ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={alertsVsValidated} margin={{ top: 10, right: 10, left: -10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="symbol" tick={{ fill: COLORS.text, fontSize: 10, angle: -45, textAnchor: "end" }} height={50} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: COLORS.text }} />
                <Bar dataKey="alerts" name="Alertes" fill={COLORS.purple} radius={[4, 4, 0, 0]} fillOpacity={0.7} />
                <Bar dataKey="entries" name="Entries" fill={COLORS.green} radius={[4, 4, 0, 0]} fillOpacity={0.8} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 7. Backtests by Date */}
        <ChartCard title="Backtests par jour (30j)" icon={<Activity className="w-4 h-4 text-pink-400" />}>
          {backtestsByDate.every((d) => d.count === 0) ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={backtestsByDate} margin={{ top: 10, right: 10, left: -10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="date" tick={{ fill: COLORS.text, fontSize: 9, angle: -45, textAnchor: "end" }} height={50} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Backtests" fill={COLORS.cyan} radius={[4, 4, 0, 0]} fillOpacity={0.8}>
                  {backtestsByDate.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={entry.date.includes("(auj)") ? COLORS.pink : COLORS.cyan}
                      fillOpacity={entry.date.includes("(auj)") ? 1 : 0.7}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 8. Average PnL by Day of Week */}
        <ChartCard title="PnL moyen par jour de la semaine" icon={<Percent className="w-4 h-4 text-emerald-400" />}>
          {pnlByDayOfWeek.every((d) => d.count === 0) ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={pnlByDayOfWeek} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis dataKey="day" tick={{ fill: COLORS.text, fontSize: 12 }} />
                <YAxis tick={{ fill: COLORS.text, fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="avgPnl" name="Moy PnL %" radius={[4, 4, 0, 0]}>
                  {pnlByDayOfWeek.map((entry, idx) => (
                    <Cell key={idx} fill={entry.avgPnl >= 0 ? COLORS.green : COLORS.red} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 9. PnL Scatter (trades vs avg PnL) */}
        <ChartCard title="PnL vs Nombre de trades (par pair)" icon={<AlertTriangle className="w-4 h-4 text-orange-400" />} span2>
          {pnlScatter.length === 0 ? (
            <EmptyState />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
                <XAxis
                  type="number"
                  dataKey="trades"
                  name="Trades"
                  tick={{ fill: COLORS.text, fontSize: 11 }}
                  label={{ value: "Nb trades", position: "insideBottom", offset: -5, fill: COLORS.text, fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="avgPnl"
                  name="Avg PnL"
                  tick={{ fill: COLORS.text, fontSize: 11 }}
                  label={{ value: "Avg PnL %", angle: -90, position: "insideLeft", fill: COLORS.text, fontSize: 11 }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null
                    const d = payload[0].payload
                    return (
                      <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
                        <p className="text-xs text-white font-medium">{d.symbol}</p>
                        <p className="text-xs text-gray-400">Trades: {d.trades}</p>
                        <p className={`text-xs font-medium ${d.avgPnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                          Avg PnL: {d.avgPnl >= 0 ? "+" : ""}{d.avgPnl}%
                        </p>
                      </div>
                    )
                  }}
                />
                <Scatter data={pnlScatter} fill={COLORS.purple}>
                  {pnlScatter.map((entry, idx) => (
                    <Cell key={idx} fill={entry.avgPnl >= 0 ? COLORS.green : COLORS.red} fillOpacity={0.7} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>
    </div>
  )
}

// --- Sub-components ---

function StatCard({
  label,
  value,
  subValue,
  icon,
  color,
}: {
  label: string
  value: string | number
  subValue?: string
  icon: React.ReactNode
  color: string
}) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-3">
      <div className={`flex items-center gap-1.5 ${color} mb-1`}>
        {icon}
        <span className="text-[10px] font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {subValue && <div className="text-xs text-green-400 mt-0.5">{subValue}</div>}
    </div>
  )
}

function ChartCard({
  title,
  icon,
  children,
  span2,
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  span2?: boolean
}) {
  return (
    <div className={`bg-gray-900/60 border border-gray-800 rounded-xl p-4 ${span2 ? "lg:col-span-2" : ""}`}>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  )
}

// ─── Day Detail Modal ─────────────────────────────────────
function DayDetailModal({ date, alerts, trades, onClose }: {
  date: string; alerts: any[]; trades: any[]; onClose: () => void
}) {
  const label = `${date.slice(8, 10)}/${date.slice(5, 7)}/${date.slice(0, 4)}`
  const wins = trades.filter(t => (t.pnl_c || 0) > 0)
  const losses = trades.filter(t => (t.pnl_c || 0) <= 0 && t.pnl_c !== undefined && t.pnl_c !== null)
  const totalPnl = trades.reduce((s, t) => s + (t.pnl_c || 0), 0)
  const wr = trades.length > 0 ? Math.round(wins.length / trades.length * 100) : 0

  // Group alerts by symbol
  const bySymbol: Record<string, { alerts: any[]; trades: any[] }> = {}
  alerts.forEach(a => {
    const sym = a.symbol || '?'
    if (!bySymbol[sym]) bySymbol[sym] = { alerts: [], trades: [] }
    bySymbol[sym].alerts.push(a)
  })
  trades.forEach(t => {
    const sym = t.symbol || '?'
    if (!bySymbol[sym]) bySymbol[sym] = { alerts: [], trades: [] }
    bySymbol[sym].trades.push(t)
  })

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div>
            <h2 className="text-xl font-bold text-gray-100">📅 Detail du {label}</h2>
            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className="text-amber-400">{alerts.length} alertes</span>
              <span className="text-cyan-400">{trades.length} trades</span>
              <span className={wr >= 60 ? "text-green-400" : wr >= 40 ? "text-yellow-400" : "text-red-400"}>WR {wr}%</span>
              <span className="text-green-400">{wins.length} WIN</span>
              <span className="text-red-400">{losses.length} LOSE</span>
              <span className={totalPnl >= 0 ? "text-green-400 font-bold" : "text-red-400 font-bold"}>PnL {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(1)}%</span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg">
            <span className="text-gray-400 text-xl">✕</span>
          </button>
        </div>

        {/* Content by symbol */}
        <div className="p-6 space-y-4">
          {Object.entries(bySymbol).sort(([, a], [, b]) => {
            const pnlA = a.trades.reduce((s, t) => s + (t.pnl_c || 0), 0)
            const pnlB = b.trades.reduce((s, t) => s + (t.pnl_c || 0), 0)
            return pnlB - pnlA
          }).map(([symbol, data]) => {
            const symPnl = data.trades.reduce((s, t) => s + (t.pnl_c || 0), 0)
            const symWins = data.trades.filter(t => (t.pnl_c || 0) > 0).length

            return (
              <div key={symbol} className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
                {/* Symbol header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-gray-200">{symbol.replace('USDT', '')}<span className="text-gray-500 font-normal">USDT</span></span>
                    <span className="text-xs text-amber-400">{data.alerts.length} alerte{data.alerts.length > 1 ? 's' : ''}</span>
                    <span className="text-xs text-cyan-400">{data.trades.length} trade{data.trades.length > 1 ? 's' : ''}</span>
                  </div>
                  {data.trades.length > 0 && (
                    <span className={`text-sm font-bold ${symPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {symPnl >= 0 ? '+' : ''}{symPnl.toFixed(1)}% ({symWins}W/{data.trades.length - symWins}L)
                    </span>
                  )}
                </div>

                {/* Alerts */}
                <div className="p-3">
                  <h4 className="text-xs text-gray-500 uppercase mb-2">Alertes</h4>
                  <div className="space-y-1">
                    {data.alerts.map((a, i) => (
                      <div key={i} className="flex items-center gap-3 text-xs text-gray-400">
                        <span className="text-gray-500 w-14">{(a.alert_datetime || '').slice(11, 16)}</span>
                        <span className="text-amber-400 w-8">S{a.score || '?'}</span>
                        <span className="text-purple-400 w-10">{a.timeframe || '?'}</span>
                        <span className="text-gray-300">${a.price_close?.toFixed(a.price_close >= 1 ? 2 : 6) || '?'}</span>
                        <span className={a.stc_validated ? "text-green-400" : "text-gray-600"}>{a.stc_validated ? 'STC✓' : 'STC✗'}</span>
                        <span className={a.has_tl_break ? "text-green-400" : "text-gray-600"}>{a.has_tl_break ? 'TL✓' : 'TL✗'}</span>
                        <span className={a.has_entry ? "text-cyan-400" : "text-gray-600"}>{a.has_entry ? 'Entry✓' : 'No entry'}</span>
                        {a.status && a.status !== 'ACTIVE' && <span className="text-red-400/60">{a.status}</span>}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Trades */}
                {data.trades.length > 0 && (
                  <div className="p-3 border-t border-gray-700/50">
                    <h4 className="text-xs text-gray-500 uppercase mb-2">Trades</h4>
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-500">
                          <th className="text-left py-1">Entree</th>
                          <th className="text-right">Prix</th>
                          <th className="text-right">SL</th>
                          <th className="text-right">TP1</th>
                          <th className="text-right">Sortie</th>
                          <th className="text-right">PnL</th>
                          <th className="text-left pl-2">Raison</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.trades.map((t, i) => {
                          const pnl = t.pnl_c || 0
                          return (
                            <tr key={i} className="border-t border-gray-800/50">
                              <td className="py-1.5 text-gray-400">{(t.entry_datetime || '').slice(0, 16).replace('T', ' ')}</td>
                              <td className="text-right text-gray-300">{t.entry_price?.toFixed(t.entry_price >= 1 ? 4 : 8)}</td>
                              <td className="text-right text-red-400/70">{t.sl_price?.toFixed(t.sl_price >= 1 ? 4 : 8)}</td>
                              <td className="text-right text-green-400/70">{t.tp1_price?.toFixed(t.tp1_price >= 1 ? 4 : 8)}</td>
                              <td className="text-right text-gray-300">{t.exit_price_c?.toFixed(t.exit_price_c >= 1 ? 4 : 8) || '—'}</td>
                              <td className={`text-right font-bold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {pnl >= 0 ? '+' : ''}{pnl.toFixed(1)}%
                              </td>
                              <td className="pl-2 text-gray-500 max-w-[150px] truncate">{t.exit_reason_c || '—'}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )
          })}

          {Object.keys(bySymbol).length === 0 && (
            <div className="text-center text-gray-500 py-8">Aucune donnee pour cette journee</div>
          )}
        </div>
      </div>
    </div>
  )
}
