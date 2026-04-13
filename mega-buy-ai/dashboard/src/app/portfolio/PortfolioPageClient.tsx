'use client'

import { useState, useEffect, useMemo } from 'react'
import { Wallet, TrendingUp, TrendingDown, RefreshCw, X, DollarSign, BarChart3, AlertTriangle, CheckCircle, XCircle, Clock, Shield, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { supabase } from '@/lib/supabase'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface Position {
  id: string
  pair: string
  entry_price: number
  current_price: number
  size_usd: number
  sl_price: number
  tp_price: number
  sl_reason: string
  tp_reason: string
  pnl_pct: number
  pnl_usd: number
  highest_price: number
  status: string
  close_reason: string | null
  exit_price: number | null
  decision: string
  confidence: number
  scanner_score: number
  is_vip: boolean
  vip_score: number
  is_high_ticket: boolean
  accumulation_days: number
  // V2+ fields
  size_remaining_pct?: number
  remaining_size_pct?: number
  tp1_price?: number
  tp1_hit?: boolean
  tp2_price?: number
  tp2_hit?: boolean
  trailing_active?: boolean
  trailing_sl?: number
  pnl_realized?: number
  realized_pnl_usd?: number
  context_score?: number
  quality_grade?: string
  opened_at: string
  closed_at: string | null
  _partial?: string
}

interface PortfolioState {
  balance: number
  initial_capital: number
  total_pnl: number
  total_trades: number
  wins: number
  losses: number
  max_drawdown_pct: number
  peak_balance: number
  drawdown_mode: boolean
  daily_loss_today: number
}

function toGMT1(dateStr: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  const utc1 = new Date(d.getTime() + 1 * 3600000)
  const dd = String(utc1.getUTCDate()).padStart(2, '0')
  const mm = String(utc1.getUTCMonth() + 1).padStart(2, '0')
  const yy = String(utc1.getUTCFullYear()).slice(-2)
  const hh = String(utc1.getUTCHours()).padStart(2, '0')
  const mn = String(utc1.getUTCMinutes()).padStart(2, '0')
  return `${dd}/${mm}/${yy} ${hh}:${mn}`
}

function formatUsd(v: number | null | undefined): string {
  const n = Number(v ?? 0)
  if (!Number.isFinite(n)) return '$0.00'
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPrice(v: number | null | undefined): string {
  const n = Number(v ?? 0)
  if (!n || !Number.isFinite(n)) return '—'
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

export default function PortfolioPageClient() {
  const [version, setVersion] = useState<'v1' | 'v2' | 'v3' | 'v4' | 'v5' | 'v6' | 'v7' | 'v8' | 'v9'>('v1')
  const [state, setState] = useState<PortfolioState | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [history, setHistory] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [tab, setTab] = useState<'overview' | 'positions' | 'history' | 'stats'>('overview')
  const [closingId, setClosingId] = useState<string | null>(null)

  // === FILTERS ===
  const [filterPair, setFilterPair] = useState('')
  const [filterDecision, setFilterDecision] = useState<string>('ALL')
  const [filterMinScore, setFilterMinScore] = useState<number>(0)
  const [filterVip, setFilterVip] = useState<'ALL' | 'VIP' | 'HT' | 'NONE'>('ALL')
  const [filterGrade, setFilterGrade] = useState<string>('ALL')
  const [filterMinPnl, setFilterMinPnl] = useState<string>('')
  const [filterMaxPnl, setFilterMaxPnl] = useState<string>('')
  const [filterReason, setFilterReason] = useState<string>('ALL')
  const [filterDateFrom, setFilterDateFrom] = useState<string>('')
  const [filterDateTo, setFilterDateTo] = useState<string>('')

  const loadV1 = async () => {
    const [portfolioRes, historyRes] = await Promise.all([
      fetch('/api/openclaw/portfolio').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/openclaw/portfolio?path=history').then(r => r.ok ? r.json() : null).catch(() => null),
    ])
    if (portfolioRes) {
      setState(portfolioRes.state || null)
      setPositions(portfolioRes.open_positions || [])
    }
    if (historyRes) {
      setHistory(historyRes.trades || [])
    }
  }

  const loadV2 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v2').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v2').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v2').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) setPositions(openRes.data as any[])
    if (closedRes.data) setHistory(closedRes.data as any[])
  }

  const loadV3 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v3').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v3').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v3').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) setPositions(openRes.data as any[])
    if (closedRes.data) setHistory(closedRes.data as any[])
  }

  const loadV5 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v5').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v5').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v5').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) setPositions(openRes.data as any[])
    if (closedRes.data) setHistory(closedRes.data as any[])
  }

  const loadV4 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v4').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v4').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v4').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) setPositions(openRes.data as any[])
    if (closedRes.data) setHistory(closedRes.data as any[])
  }

  const loadV6 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v6').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v6').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v6').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) setPositions(openRes.data as any[])
    if (closedRes.data) setHistory(closedRes.data as any[])
  }

  const loadV7 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v7').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v7').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v7').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) {
      // Map V7 fields to common Position interface (tp1_price, tp2_price, etc.)
      const mapped = openRes.data.map((p: any) => ({
        ...p,
        tp1_hit: p.partial1_done,
        tp2_hit: p.partial2_done,
        trailing_active: p.trail_active,
        trailing_sl: p.trail_stop,
        size_remaining_pct: Math.round((p.remaining_size_pct || 1) * 100),
        pnl_realized: p.realized_pnl_usd,
      }))
      setPositions(mapped as any[])
    }
    if (closedRes.data) {
      const mapped = closedRes.data.map((p: any) => ({
        ...p,
        tp1_hit: p.partial1_done,
        tp2_hit: p.partial2_done,
        trailing_active: p.trail_active,
        pnl_realized: p.realized_pnl_usd,
      }))
      setHistory(mapped as any[])
    }
  }

  const loadV8 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v8').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v8').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v8').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) setPositions(openRes.data as any[])
    if (closedRes.data) setHistory(closedRes.data as any[])
  }

  const loadV9 = async () => {
    const [stateRes, openRes, closedRes] = await Promise.all([
      supabase.from('openclaw_portfolio_state_v9').select('*').eq('id', 'main').single(),
      supabase.from('openclaw_positions_v9').select('*').eq('status', 'OPEN').order('opened_at', { ascending: false }),
      supabase.from('openclaw_positions_v9').select('*').eq('status', 'CLOSED').order('closed_at', { ascending: false }).limit(200),
    ])
    if (stateRes.data) setState(stateRes.data as any)
    if (openRes.data) {
      const mapped = openRes.data.map((p: any) => ({
        ...p,
        tp1_hit: p.partial1_done, tp2_hit: p.partial2_done,
        trailing_active: p.trail_active, trailing_sl: p.trail_stop,
        size_remaining_pct: Math.round((p.remaining_size_pct || 1) * 100),
        pnl_realized: p.realized_pnl_usd,
      }))
      setPositions(mapped as any[])
    }
    if (closedRes.data) {
      const mapped = closedRes.data.map((p: any) => ({
        ...p,
        tp1_hit: p.partial1_done, tp2_hit: p.partial2_done,
        trailing_active: p.trail_active, pnl_realized: p.realized_pnl_usd,
      }))
      setHistory(mapped as any[])
    }
  }

  const loadData = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)
    try {
      if (version === 'v1') await loadV1()
      else if (version === 'v2') await loadV2()
      else if (version === 'v3') await loadV3()
      else if (version === 'v4') await loadV4()
      else if (version === 'v5') await loadV5()
      else if (version === 'v6') await loadV6()
      else if (version === 'v7') await loadV7()
      else if (version === 'v8') await loadV8()
      else await loadV9()
    } catch {}
    setLoading(false)
    setRefreshing(false)
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(() => loadData(true), 30000)
    return () => clearInterval(interval)
  }, [version])

  const handleClose = async (posId: string) => {
    setClosingId(posId)
    try {
      await fetch('/api/openclaw/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'close', position_id: posId }),
      })
      setTimeout(() => loadData(true), 2000)
    } catch {}
    setClosingId(null)
  }

  const handleForceCheck = async () => {
    setRefreshing(true)
    try {
      await fetch('/api/openclaw/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'check' }),
      })
      setTimeout(() => loadData(true), 3000)
    } catch {}
    setRefreshing(false)
  }

  // === FILTERING (hooks must run BEFORE any early return) ===
  const filteredPositions = useMemo(() => {
    return positions.filter(p => {
      if (filterPair && !p.pair.toLowerCase().includes(filterPair.toLowerCase())) return false
      if (filterDecision !== 'ALL' && p.decision !== filterDecision) return false
      if (filterMinScore > 0 && (p.scanner_score || 0) < filterMinScore) return false
      if (filterVip === 'VIP' && !p.is_vip) return false
      if (filterVip === 'HT' && !p.is_high_ticket) return false
      if (filterVip === 'NONE' && (p.is_vip || p.is_high_ticket)) return false
      if (filterGrade !== 'ALL' && p.quality_grade !== filterGrade) return false
      if (filterMinPnl !== '' && (p.pnl_pct || 0) < parseFloat(filterMinPnl)) return false
      if (filterMaxPnl !== '' && (p.pnl_pct || 0) > parseFloat(filterMaxPnl)) return false
      if (filterReason !== 'ALL' && p.close_reason !== filterReason) return false
      if (filterDateFrom && p.opened_at && new Date(p.opened_at) < new Date(filterDateFrom)) return false
      if (filterDateTo && p.opened_at && new Date(p.opened_at) > new Date(filterDateTo + 'T23:59:59')) return false
      return true
    })
  }, [positions, filterPair, filterDecision, filterMinScore, filterVip, filterGrade, filterMinPnl, filterMaxPnl, filterReason, filterDateFrom, filterDateTo])

  // Build partial TP events from open positions (V7 hybrid trailing)
  const partialEvents = useMemo(() => {
    const events: (Position & { _partial?: string })[] = []
    for (const p of positions) {
      if (p.tp1_hit) {
        const tp1Pct = 10
        const tp1Size = (p.size_usd || 0) * 0.5
        const tp1Pnl = tp1Size * tp1Pct / 100
        events.push({
          ...p,
          id: p.id + '_tp1',
          _partial: 'TP1',
          status: 'PARTIAL',
          close_reason: 'TP1_PARTIAL',
          pnl_pct: tp1Pct,
          pnl_usd: tp1Pnl,
          size_usd: tp1Size,
          exit_price: p.tp1_price || (p.entry_price * 1.1),
        })
      }
      if (p.tp2_hit) {
        const tp2Pct = 20
        const tp2Size = (p.size_usd || 0) * 0.3
        const tp2Pnl = tp2Size * tp2Pct / 100
        events.push({
          ...p,
          id: p.id + '_tp2',
          _partial: 'TP2',
          status: 'PARTIAL',
          close_reason: 'TP2_PARTIAL',
          pnl_pct: tp2Pct,
          pnl_usd: tp2Pnl,
          size_usd: tp2Size,
          exit_price: p.tp2_price || (p.entry_price * 1.2),
        })
      }
    }
    return events
  }, [positions])

  const filteredHistory = useMemo(() => {
    const allEntries = [...partialEvents, ...history]
    return allEntries.filter(p => {
      if (filterPair && !p.pair.toLowerCase().includes(filterPair.toLowerCase())) return false
      if (filterDecision !== 'ALL' && p.decision !== filterDecision) return false
      if (filterMinScore > 0 && (p.scanner_score || 0) < filterMinScore) return false
      if (filterVip === 'VIP' && !p.is_vip) return false
      if (filterVip === 'HT' && !p.is_high_ticket) return false
      if (filterVip === 'NONE' && (p.is_vip || p.is_high_ticket)) return false
      if (filterGrade !== 'ALL' && p.quality_grade !== filterGrade) return false
      if (filterMinPnl !== '' && (p.pnl_pct || 0) < parseFloat(filterMinPnl)) return false
      if (filterMaxPnl !== '' && (p.pnl_pct || 0) > parseFloat(filterMaxPnl)) return false
      if (filterReason !== 'ALL' && p.close_reason !== filterReason) return false
      if (filterDateFrom && p.opened_at && new Date(p.opened_at) < new Date(filterDateFrom)) return false
      if (filterDateTo && p.opened_at && new Date(p.opened_at) > new Date(filterDateTo + 'T23:59:59')) return false
      return true
    })
  }, [history, partialEvents, filterPair, filterDecision, filterMinScore, filterVip, filterGrade, filterMinPnl, filterMaxPnl, filterReason, filterDateFrom, filterDateTo])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
      </div>
    )
  }

  const rawState = state || {} as any
  const s = {
    balance: Number(rawState.balance ?? 5000),
    initial_capital: Number(rawState.initial_capital ?? 5000),
    total_pnl: Number(rawState.total_pnl ?? 0),
    total_trades: Number(rawState.total_trades ?? 0),
    wins: Number(rawState.wins ?? 0),
    losses: Number(rawState.losses ?? 0),
    max_drawdown_pct: Number(rawState.max_drawdown_pct ?? 0),
    peak_balance: Number(rawState.peak_balance ?? 5000),
    drawdown_mode: Boolean(rawState.drawdown_mode ?? false),
    daily_loss_today: Number(rawState.daily_loss_today ?? 0),
  }
  const wr = s.total_trades > 0 ? (s.wins / s.total_trades * 100) : 0
  // WR total: includes partial TP hits from open positions as wins
  const partialWins = positions.filter(p => p.tp1_hit || p.tp2_hit).length
  const totalWins = s.wins + partialWins
  const totalTrades = s.total_trades + partialWins
  const wrTotal = totalTrades > 0 ? (totalWins / totalTrades * 100) : 0
  const returnPct = s.initial_capital > 0 ? (s.total_pnl / s.initial_capital * 100) : 0
  const inPositions = positions.reduce((sum, p) => {
    const size = Number(p.size_usd) || 0
    const rem = p.remaining_size_pct != null ? Number(p.remaining_size_pct) : 1
    return sum + size * (isNaN(rem) ? 1 : rem)
  }, 0)
  const realizedInOpen = positions.reduce((sum, p) => sum + (Number(p.realized_pnl_usd) || 0), 0)
  const unrealizedPnl = positions.reduce((sum, p) => {
    const pnlPct = Number(p.pnl_pct) || 0
    const size = Number(p.size_usd) || 0
    const rem = p.remaining_size_pct != null ? Number(p.remaining_size_pct) : 1
    const remaining = isNaN(rem) ? 1 : rem
    return sum + (size * remaining * pnlPct / 100)
  }, 0)
  const equity = s.balance + inPositions + unrealizedPnl

  const resetFilters = () => {
    setFilterPair(''); setFilterDecision('ALL'); setFilterMinScore(0); setFilterVip('ALL')
    setFilterGrade('ALL'); setFilterMinPnl(''); setFilterMaxPnl(''); setFilterReason('ALL')
    setFilterDateFrom(''); setFilterDateTo('')
  }
  const activeFilterCount = [
    filterPair, filterDecision !== 'ALL', filterMinScore > 0, filterVip !== 'ALL',
    filterGrade !== 'ALL', filterMinPnl, filterMaxPnl, filterReason !== 'ALL',
    filterDateFrom, filterDateTo
  ].filter(Boolean).length

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-green-500/10 rounded-xl">
            <Wallet className="w-7 h-7 text-green-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Portfolio OpenClaw {version !== 'v1' ? version.toUpperCase() : ''}</h1>
            <p className="text-sm text-gray-500">{
              version === 'v1' ? 'V1 — TP fixe +10% / SL -8%' :
              version === 'v2' ? 'V2 — TP partiel + Trailing Stop' :
              version === 'v3' ? 'V3 — 95% Conf | 3% × 25pos × Timeout 48h' :
              version === 'v4' ? 'V4 — Gate: Score>=8 + VIP/HT + Green4H' :
              version === 'v5' ? 'V5 — Combo: 95% + Green4H + 24h>0% | 81.8% WR' :
              version === 'v6' ? 'V6 — Body 4H≥3% + Fixed TP+15% | 12 slots × 8% × $5K' :
              version === 'v7' ? 'V7 — Body 4H≥3% + Hybrid Trailing | TP1 50%@+10% + TP2 30%@+20% + 20% Trail' :
              version === 'v8' ? 'V8 — V6 + Ultra Filter (ADX 15-35 + BTC Bull + 24h>=1%) | Fixed TP+15%' :
              'V9 — V7 + Ultra Filter (ADX 15-35 + BTC Bull + 24h>=1%) | Hybrid Trailing'
            }</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* V1/V2 Toggle */}
          <div className="flex items-center bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            <button onClick={() => setVersion('v1')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v1' ? "bg-green-500/20 text-green-300" : "text-gray-500 hover:text-gray-300")}>
              V1
            </button>
            <button onClick={() => setVersion('v2')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v2' ? "bg-purple-500/20 text-purple-300" : "text-gray-500 hover:text-gray-300")}>
              V2
            </button>
            <button onClick={() => setVersion('v3')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v3' ? "bg-cyan-500/20 text-cyan-300" : "text-gray-500 hover:text-gray-300")}>
              V3
            </button>
            <button onClick={() => setVersion('v4')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v4' ? "bg-amber-500/20 text-amber-300" : "text-gray-500 hover:text-gray-300")}>
              V4
            </button>
            <button onClick={() => setVersion('v5')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v5' ? "bg-emerald-500/20 text-emerald-300" : "text-gray-500 hover:text-gray-300")}>
              V5
            </button>
            <button onClick={() => setVersion('v6')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v6' ? "bg-pink-500/20 text-pink-300" : "text-gray-500 hover:text-gray-300")}>
              V6
            </button>
            <button onClick={() => setVersion('v7')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v7' ? "bg-rose-500/20 text-rose-300" : "text-gray-500 hover:text-gray-300")}>
              V7
            </button>
            <button onClick={() => setVersion('v8')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v8' ? "bg-amber-500/20 text-amber-300" : "text-gray-500 hover:text-gray-300")}>
              V8
            </button>
            <button onClick={() => setVersion('v9')} className={cn("px-3 py-2 text-sm font-medium transition-colors", version === 'v9' ? "bg-amber-500/20 text-amber-300" : "text-gray-500 hover:text-gray-300")}>
              V9
            </button>
          </div>
          {version === 'v1' && (
            <button onClick={handleForceCheck} className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors border border-gray-700">
              <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} /> Check
            </button>
          )}
          <button onClick={() => loadData(true)} className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors border border-gray-700">
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} /> Refresh
          </button>
        </div>
      </div>

      {/* Drawdown warning */}
      {s.drawdown_mode && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-red-400" />
          <div>
            <p className="text-red-400 font-medium">Mode Drawdown Actif — Tailles reduites de 50%</p>
            <p className="text-red-400/70 text-sm">Max drawdown depasse 15%. OpenClaw continue de trader avec prudence.</p>
          </div>
        </div>
      )}

      {/* Main Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-9 gap-3">
        <StatCard label="Equity" value={formatUsd(equity)} icon={<Wallet className="w-4 h-4" />} color={equity >= s.initial_capital ? "text-green-400" : "text-red-400"} />
        <StatCard label="Balance" value={formatUsd(s.balance)} sub={`Initial: ${formatUsd(s.initial_capital)}`} icon={<DollarSign className="w-4 h-4" />} color="text-cyan-400" />
        <StatCard label="PnL Total" value={`${s.total_pnl >= 0 ? '+' : ''}${formatUsd(s.total_pnl)}`} sub={`${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%`} icon={<TrendingUp className="w-4 h-4" />} color={s.total_pnl >= 0 ? "text-green-400" : "text-red-400"} />
        <StatCard label="Non-realise" value={`${unrealizedPnl >= 0 ? '+' : ''}${formatUsd(unrealizedPnl)}`} sub={`${positions.length} positions`} icon={<BarChart3 className="w-4 h-4" />} color={unrealizedPnl >= 0 ? "text-green-400" : "text-red-400"} />
        <StatCard label="WR Total" value={`${wrTotal.toFixed(1)}%`} sub={`${totalWins}W / ${s.losses}L (${totalTrades}) +${partialWins} TP`} icon={<Activity className="w-4 h-4" />} color={wrTotal >= 50 ? "text-green-400" : "text-yellow-400"} />
        <StatCard label="WR Fermes" value={`${wr.toFixed(1)}%`} sub={`${s.wins}W / ${s.losses}L (${s.total_trades})`} icon={<CheckCircle className="w-4 h-4" />} color={wr >= 50 ? "text-green-400" : "text-yellow-400"} />
        <StatCard label="Positions" value={`${positions.length}/${version === 'v3' || version === 'v5' ? 25 : version === 'v4' ? 15 : (version === 'v6' || version === 'v7' || version === 'v8' || version === 'v9') ? 12 : 10}`} sub={`$${inPositions.toFixed(0)} alloc`} icon={<BarChart3 className="w-4 h-4" />} color="text-purple-400" />
        <StatCard label="Max DD" value={`${s.max_drawdown_pct.toFixed(1)}%`} sub={s.drawdown_mode ? '⚠️ ACTIF' : 'OK'} icon={<Shield className="w-4 h-4" />} color={s.max_drawdown_pct > 10 ? "text-red-400" : "text-green-400"} />
        <StatCard label="Perte Jour" value={`${formatUsd(s.daily_loss_today)}`} sub="max 5%" icon={<AlertTriangle className="w-4 h-4" />} color={s.daily_loss_today > s.initial_capital * 0.03 ? "text-orange-400" : "text-gray-400"} />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        {(['overview', 'positions', 'history', 'stats'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} className={cn(
            "px-4 py-2 rounded-lg text-sm font-medium transition-colors border",
            tab === t ? "bg-green-500/20 border-green-500/40 text-green-300" : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700"
          )}>
            {t === 'overview' ? `Positions Ouvertes (${filteredPositions.length}${activeFilterCount > 0 ? `/${positions.length}` : ''})` : t === 'positions' ? 'Details' : t === 'history' ? `Historique (${filteredHistory.length}${activeFilterCount > 0 ? `/${history.length}` : ''})` : 'Statistiques'}
          </button>
        ))}
      </div>

      {/* Filter Bar */}
      {(tab === 'overview' || tab === 'positions' || tab === 'history') && (
        <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase">Filtres {activeFilterCount > 0 && <span className="ml-2 px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px]">{activeFilterCount} actif{activeFilterCount > 1 ? 's' : ''}</span>}</span>
            {activeFilterCount > 0 && (
              <button onClick={resetFilters} className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1">
                <X className="w-3 h-3" /> Reset
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
            <input
              type="text"
              value={filterPair}
              onChange={e => setFilterPair(e.target.value)}
              placeholder="Pair (BTCUSDT...)"
              className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-green-500/50"
            />
            <select value={filterDecision} onChange={e => setFilterDecision(e.target.value)} className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-green-500/50">
              <option value="ALL">Decision (toutes)</option>
              <option value="BUY STRONG">BUY STRONG</option>
              <option value="BUY">BUY</option>
              <option value="BUY WEAK">BUY WEAK</option>
            </select>
            <select value={filterVip} onChange={e => setFilterVip(e.target.value as any)} className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-green-500/50">
              <option value="ALL">VIP (tous)</option>
              <option value="HT">🏆 High Ticket</option>
              <option value="VIP">⭐ VIP</option>
              <option value="NONE">Sans badge</option>
            </select>
            <select value={filterGrade} onChange={e => setFilterGrade(e.target.value)} className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-green-500/50">
              <option value="ALL">Grade (tous)</option>
              <option value="A+">A+</option>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
            <input
              type="number"
              min="0" max="10"
              value={filterMinScore || ''}
              onChange={e => setFilterMinScore(parseInt(e.target.value) || 0)}
              placeholder="Score min (0-10)"
              className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-green-500/50"
            />
            <input
              type="number"
              value={filterMinPnl}
              onChange={e => setFilterMinPnl(e.target.value)}
              placeholder="PnL min %"
              className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-green-500/50"
            />
            <input
              type="number"
              value={filterMaxPnl}
              onChange={e => setFilterMaxPnl(e.target.value)}
              placeholder="PnL max %"
              className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-green-500/50"
            />
            <select value={filterReason} onChange={e => setFilterReason(e.target.value)} className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-green-500/50">
              <option value="ALL">Raison (toutes)</option>
              <option value="TP_HIT">TP HIT</option>
              <option value="SL_HIT">SL HIT</option>
              <option value="TIMEOUT_48H">TIMEOUT 48H</option>
              <option value="TIMEOUT_72H">TIMEOUT 72H</option>
              <option value="TRAIL_STOP">TRAIL STOP</option>
              <option value="BREAKEVEN_STOP">BREAKEVEN</option>
              <option value="MANUAL">MANUAL</option>
              <option value="EXPIRED">EXPIRED</option>
            </select>
            <input
              type="date"
              value={filterDateFrom}
              onChange={e => setFilterDateFrom(e.target.value)}
              className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-green-500/50"
            />
            <input
              type="date"
              value={filterDateTo}
              onChange={e => setFilterDateTo(e.target.value)}
              className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-green-500/50"
            />
          </div>
        </div>
      )}

      {/* Content */}
      {(tab === 'overview' || tab === 'positions') && (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                <th className="px-4 py-3 text-left">Paire</th>
                <th className="px-4 py-3 text-center">VIP</th>
                {(version === 'v2' || version === 'v7' || version === 'v9') && <th className="px-4 py-3 text-center">Ctx</th>}
                {(version === 'v2' || version === 'v6' || version === 'v7') && <th className="px-4 py-3 text-center">Grade</th>}
                {(version === 'v6' || version === 'v7' || version === 'v8' || version === 'v9') && <th className="px-4 py-3 text-center">Score</th>}
                <th className="px-4 py-3 text-center">Decision</th>
                <th className="px-4 py-3 text-right">Size</th>
                {(version === 'v2' || version === 'v7' || version === 'v9') && <th className="px-4 py-3 text-center">Remaining</th>}
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Actuel</th>
                <th className="px-4 py-3 text-right">PnL</th>
                {(version === 'v2' || version === 'v7' || version === 'v9') && <th className="px-4 py-3 text-right">Realise</th>}
                <th className="px-4 py-3 text-right">SL</th>
                {(version === 'v1' || version === 'v6' || version === 'v8') && <th className="px-4 py-3 text-right">TP</th>}
                {(version === 'v2' || version === 'v7' || version === 'v9') && <th className="px-4 py-3 text-center">TP1</th>}
                {(version === 'v2' || version === 'v7' || version === 'v9') && <th className="px-4 py-3 text-center">TP2</th>}
                {(version === 'v2' || version === 'v7' || version === 'v9') && <th className="px-4 py-3 text-center">Trail</th>}
                <th className="px-4 py-3 text-left">Ouvert</th>
                <th className="px-3 py-3 text-center">Timer</th>
                {version === 'v1' && <th className="px-4 py-3 text-center">Action</th>}
              </tr>
            </thead>
            <tbody>
              {filteredPositions.map(p => (
                <tr key={p.id} className="border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-200">{p.pair.replace('USDT', '')}<span className="text-gray-600">USDT</span></td>
                  <td className="px-4 py-3 text-center">
                    {p.is_high_ticket ? <span title={`VIP ${p.vip_score}/5 — High Ticket`} className="text-base cursor-help">🏆</span>
                      : p.is_vip ? <span title={`VIP ${p.vip_score}/5`} className="text-base cursor-help">⭐</span>
                      : <span className="text-gray-700 text-xs">—</span>}
                  </td>
                  {(version === 'v2' || version === 'v7' || version === 'v9') && <td className="px-4 py-3 text-center">
                    <span className={cn("text-xs font-bold", (p.context_score || 0) >= 5 ? "text-green-400" : (p.context_score || 0) >= 4 ? "text-cyan-400" : (p.context_score || 0) >= 3 ? "text-yellow-400" : "text-gray-500")}>
                      {p.context_score || 0}/5
                    </span>
                  </td>}
                  {(version === 'v2' || version === 'v6' || version === 'v7') && <td className="px-4 py-3 text-center">
                    <span className={cn("text-xs font-medium", p.quality_grade === 'A+' ? "text-green-400 font-bold" : p.quality_grade === 'A' ? "text-green-400" : p.quality_grade === 'B' ? "text-yellow-400" : "text-gray-500")}>
                      {p.quality_grade || '—'}
                    </span>
                  </td>}
                  {(version === 'v6' || version === 'v7' || version === 'v8' || version === 'v9') && <td className="px-4 py-3 text-center">
                    <span className={cn("text-xs font-bold", (p.scanner_score || 0) >= 9 ? "text-green-400" : (p.scanner_score || 0) >= 7 ? "text-cyan-400" : "text-yellow-400")}>
                      {p.scanner_score || 0}/10
                    </span>
                  </td>}
                  <td className="px-4 py-3 text-center">
                    <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium",
                      p.decision?.includes('STRONG') ? "bg-green-500/15 text-green-400" :
                      p.decision === 'BUY' ? "bg-green-500/10 text-green-300" :
                      "bg-lime-500/10 text-lime-400"
                    )}>{p.decision}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">{formatUsd(p.size_usd)}</td>
                  {(version === 'v2' || version === 'v7' || version === 'v9') && <td className="px-4 py-3 text-center">
                    <span className="text-xs text-gray-400">{p.size_remaining_pct || 100}%</span>
                  </td>}
                  <td className="px-4 py-3 text-right text-gray-400 font-mono">{formatPrice(p.entry_price)}</td>
                  <td className="px-4 py-3 text-right text-gray-200 font-mono">{formatPrice(p.current_price || p.entry_price)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className={cn("font-mono font-medium", p.pnl_pct >= 0 ? "text-green-400" : "text-red-400")}>
                      {p.pnl_pct >= 0 ? '+' : ''}{p.pnl_pct?.toFixed(2)}%
                    </span>
                    <br />
                    <span className={cn("text-xs", p.pnl_usd >= 0 ? "text-green-400/60" : "text-red-400/60")}>
                      {p.pnl_usd >= 0 ? '+' : ''}{formatUsd(p.pnl_usd || 0)}
                    </span>
                  </td>
                  {(version === 'v2' || version === 'v7' || version === 'v9') && <td className="px-4 py-3 text-right">
                    <span className={cn("font-mono text-xs", (p.pnl_realized || 0) >= 0 ? "text-green-400/70" : "text-red-400/70")}>
                      {(p.pnl_realized || 0) >= 0 ? '+' : ''}{formatUsd(p.pnl_realized || 0)}
                    </span>
                  </td>}
                  <td className="px-4 py-3 text-right">
                    <span className="text-red-400/80 font-mono text-xs">{formatPrice(p.sl_price)}</span>
                    <br /><span className="text-[10px] text-gray-600">{p.sl_reason}</span>
                  </td>
                  {(version === 'v1' || version === 'v6' || version === 'v8') && <td className="px-4 py-3 text-right">
                    <span className="text-green-400/80 font-mono text-xs">{formatPrice(p.tp_price)}</span>
                    <br /><span className="text-[10px] text-gray-600">{p.tp_reason || (version === 'v6' ? '+15%' : '')}</span>
                  </td>}
                  {(version === 'v2' || version === 'v7' || version === 'v9') && <td className="px-4 py-3 text-center">
                    {p.tp1_hit ? <span className="text-green-400 text-xs font-bold">✅ +10%</span> : <span className="text-gray-600 text-xs">{formatPrice(p.tp1_price || 0)}</span>}
                  </td>}
                  {(version === 'v2' || version === 'v7' || version === 'v9') && <td className="px-4 py-3 text-center">
                    {p.tp2_hit ? <span className="text-green-400 text-xs font-bold">✅ +20%</span> : <span className="text-gray-600 text-xs">{formatPrice(p.tp2_price || 0)}</span>}
                  </td>}
                  {(version === 'v2' || version === 'v7' || version === 'v9') && <td className="px-4 py-3 text-center">
                    {p.trailing_active ? <span className="text-purple-400 text-xs font-bold">🔄 ON</span> : <span className="text-gray-700 text-xs">—</span>}
                  </td>}
                  <td className="px-4 py-3 text-gray-400 text-xs">{toGMT1(p.opened_at)}</td>
                  <td className="px-3 py-3 text-center">
                    {(() => {
                      const timeoutH = (version === 'v7' || version === 'v9') ? 72 : (version === 'v6' || version === 'v8') ? 48 : version === 'v5' ? 168 : version === 'v4' ? 168 : version === 'v3' ? 168 : version === 'v2' ? 168 : 168
                      const opened = new Date(p.opened_at)
                      const now = new Date()
                      const elapsedH = (now.getTime() - opened.getTime()) / 3600000
                      const remainH = Math.max(0, timeoutH - elapsedH)
                      const pct = Math.min(100, elapsedH / timeoutH * 100)
                      const elD = Math.floor(elapsedH / 24); const elH = Math.floor(elapsedH % 24)
                      const remD = Math.floor(remainH / 24); const remH = Math.floor(remainH % 24)
                      const urgentColor = remainH <= 6 ? 'text-red-400' : remainH <= 12 ? 'text-orange-400' : remainH <= 24 ? 'text-yellow-400' : 'text-gray-400'
                      return (
                        <div className="space-y-0.5">
                          <div className="text-[10px] text-gray-500">{elD > 0 ? `${elD}j ${elH}h` : `${elH}h`}</div>
                          <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
                            <div className={cn("h-full rounded-full", pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-orange-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-green-500')} style={{width: `${pct}%`}} />
                          </div>
                          <div className={cn("text-[10px] font-medium", urgentColor)}>
                            {remainH <= 0 ? '⏰ EXPIRED' : remD > 0 ? `${remD}j ${remH}h` : `${remH}h`}
                          </div>
                        </div>
                      )
                    })()}
                  </td>
                  {version === 'v1' && <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleClose(p.id)}
                      disabled={closingId === p.id}
                      className="px-2 py-1 text-xs bg-red-500/10 text-red-400 border border-red-500/20 rounded hover:bg-red-500/20 disabled:opacity-30"
                    >
                      {closingId === p.id ? '...' : 'Fermer'}
                    </button>
                  </td>}
                </tr>
              ))}
              {filteredPositions.length === 0 && (
                <tr><td colSpan={14} className="px-4 py-12 text-center text-gray-500">{positions.length === 0 ? 'Aucune position ouverte — OpenClaw attend des signaux BUY' : 'Aucune position ne correspond aux filtres'}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'history' && (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                <th className="px-4 py-3 text-left">Paire</th>
                <th className="px-4 py-3 text-center">VIP</th>
                <th className="px-4 py-3 text-center">Accum</th>
                <th className="px-4 py-3 text-center">Resultat</th>
                <th className="px-4 py-3 text-right">PnL</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Exit</th>
                <th className="px-4 py-3 text-right">Size</th>
                <th className="px-4 py-3 text-center">Raison</th>
                <th className="px-4 py-3 text-left">Ouvert</th>
                <th className="px-4 py-3 text-left">Ferme</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.map(p => {
                const isPartial = (p as any)._partial
                return (
                <tr key={p.id} className={cn("border-b border-gray-800/50 hover:bg-gray-800/40", isPartial && "bg-purple-500/5 border-l-2 border-l-purple-500")}>
                  <td className="px-4 py-3 font-medium text-gray-200">
                    {p.pair.replace('USDT', '')}<span className="text-gray-600">USDT</span>
                    {isPartial && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 font-medium">{isPartial}</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {p.is_high_ticket ? <span title={`VIP ${p.vip_score}/5 — High Ticket`} className="text-base cursor-help">🏆</span>
                      : p.is_vip ? <span title={`VIP ${p.vip_score}/5`} className="text-base cursor-help">⭐</span>
                      : <span className="text-gray-700 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {(p.accumulation_days || 0) > 0 ? (
                      <span className={cn("text-xs font-medium", p.accumulation_days >= 5 ? "text-green-400" : p.accumulation_days >= 3 ? "text-yellow-400" : "text-gray-400")}>
                        {p.accumulation_days.toFixed(1)}j
                      </span>
                    ) : <span className="text-gray-700 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {isPartial ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/15 text-purple-400">
                        🎯 {isPartial === 'TP1' ? '50% vendu' : '30% vendu'}
                      </span>
                    ) : (
                      <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium",
                        (p.pnl_pct || 0) >= 0 ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400"
                      )}>
                        {(p.pnl_pct || 0) >= 0 ? '✅ WIN' : '❌ LOSE'}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className={cn("font-mono font-bold", isPartial ? "text-purple-400" : (p.pnl_pct || 0) >= 0 ? "text-green-400" : "text-red-400")}>
                      {(p.pnl_pct || 0) >= 0 ? '+' : ''}{(p.pnl_pct || 0).toFixed(2)}%
                    </span>
                    <br />
                    <span className="text-xs text-gray-500">{(p.pnl_usd || 0) >= 0 ? '+' : ''}{formatUsd(p.pnl_usd || 0)}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400 font-mono text-xs">{formatPrice(p.entry_price)}</td>
                  <td className="px-4 py-3 text-right text-gray-300 font-mono text-xs">{formatPrice(p.exit_price || 0)}</td>
                  <td className="px-4 py-3 text-right text-gray-400">{formatUsd(p.size_usd)}</td>
                  <td className="px-4 py-3 text-center">
                    {isPartial ? (
                      <span className="text-xs font-medium text-purple-400">{isPartial === 'TP1' ? 'TP1 +10%' : 'TP2 +20%'}</span>
                    ) : (
                      <span className="text-xs text-gray-500">{p.close_reason || '—'}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{toGMT1(p.opened_at)}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{isPartial ? <span className="text-purple-400/60">en cours</span> : toGMT1(p.closed_at || '')}</td>
                </tr>
                )
              })}
              {filteredHistory.length === 0 && (
                <tr><td colSpan={11} className="px-4 py-12 text-center text-gray-500">{history.length === 0 ? 'Aucun trade cloture — les positions sont encore ouvertes' : 'Aucun trade ne correspond aux filtres'}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'stats' && (
        <StatsTab history={filteredHistory} initialCapital={s.initial_capital} />
      )}
    </div>
  )
}

// ======================== STATS TAB ========================

const COLORS = {
  green: '#4ade80',
  red: '#f87171',
  purple: '#a78bfa',
  gray: '#6b7280',
  grid: '#374151',
  text: '#9ca3af',
  lime: '#a3e635',
  orange: '#fb923c',
  cyan: '#22d3ee',
  darkGreen: '#16a34a',
}

const DECISION_COLORS: Record<string, string> = {
  'BUY STRONG': COLORS.darkGreen,
  'BUY': COLORS.green,
  'BUY WEAK': COLORS.lime,
}

const CLOSE_REASON_COLORS: Record<string, string> = {
  'TP_HIT': COLORS.green,
  'SL_HIT': COLORS.red,
  'MANUAL': COLORS.gray,
  'EXPIRED': COLORS.orange,
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
      <h3 className="text-sm font-medium text-gray-300 mb-3">{title}</h3>
      {children}
    </div>
  )
}

function MiniStatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-3 text-center">
      <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">{label}</div>
      <div className={cn("text-lg font-bold", color || "text-gray-200")}>{value}</div>
    </div>
  )
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color }} className="font-medium">
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
        </p>
      ))}
    </div>
  )
}

function StatsTab({ history, initialCapital }: { history: Position[]; initialCapital: number }) {
  const stats = useMemo(() => {
    if (history.length === 0) return null

    const sorted = [...history].sort((a, b) => new Date(a.opened_at).getTime() - new Date(b.opened_at).getTime())

    // --- Equity Curve ---
    let cumPnl = 0
    const equityData = sorted.map((t, i) => {
      cumPnl += (t.pnl_usd || 0)
      return {
        name: `#${i + 1}`,
        equity: initialCapital + cumPnl,
        baseline: initialCapital,
        pair: t.pair.replace('USDT', ''),
      }
    })

    // --- PnL per Trade ---
    const pnlPerTrade = sorted.map((t, i) => ({
      name: t.pair.replace('USDT', ''),
      pnl: t.pnl_usd || 0,
      fill: (t.pnl_usd || 0) >= 0 ? COLORS.green : COLORS.red,
    }))

    // --- Win Rate by Decision ---
    const decisionMap: Record<string, { wins: number; losses: number; total: number }> = {}
    sorted.forEach(t => {
      const d = t.decision || 'UNKNOWN'
      if (!decisionMap[d]) decisionMap[d] = { wins: 0, losses: 0, total: 0 }
      decisionMap[d].total++
      if ((t.pnl_usd || 0) >= 0) decisionMap[d].wins++
      else decisionMap[d].losses++
    })
    const winRateByDecision = Object.entries(decisionMap).map(([d, v]) => ({
      name: d,
      winRate: v.total > 0 ? (v.wins / v.total * 100) : 0,
      lossRate: v.total > 0 ? (v.losses / v.total * 100) : 0,
      count: v.total,
    }))

    // --- PnL Distribution ---
    const ranges = [
      { label: '< -10', min: -Infinity, max: -10 },
      { label: '-10 a -5', min: -10, max: -5 },
      { label: '-5 a 0', min: -5, max: 0 },
      { label: '0 a 5', min: 0, max: 5 },
      { label: '5 a 10', min: 5, max: 10 },
      { label: '> 10', min: 10, max: Infinity },
    ]
    const pnlDistribution = ranges.map(r => {
      const count = sorted.filter(t => {
        const pnl = t.pnl_usd || 0
        return pnl >= r.min && pnl < r.max
      }).length
      return { name: r.label, count, fill: r.min >= 0 ? COLORS.green : COLORS.red }
    })

    // --- Decision Pie ---
    const decisionPie = Object.entries(decisionMap).map(([d, v]) => ({
      name: d,
      value: v.total,
      color: DECISION_COLORS[d] || COLORS.purple,
    }))

    // --- Close Reason Pie ---
    const reasonMap: Record<string, number> = {}
    sorted.forEach(t => {
      const r = t.close_reason || 'UNKNOWN'
      reasonMap[r] = (reasonMap[r] || 0) + 1
    })
    const closeReasonPie = Object.entries(reasonMap).map(([r, v]) => ({
      name: r,
      value: v,
      color: CLOSE_REASON_COLORS[r] || COLORS.purple,
    }))

    // --- Top Pairs ---
    const pairMap: Record<string, number> = {}
    sorted.forEach(t => {
      const p = t.pair.replace('USDT', '')
      pairMap[p] = (pairMap[p] || 0) + (t.pnl_usd || 0)
    })
    const topPairs = Object.entries(pairMap)
      .map(([p, pnl]) => ({ name: p, pnl, fill: pnl >= 0 ? COLORS.green : COLORS.red }))
      .sort((a, b) => b.pnl - a.pnl)

    // --- Trade Duration Distribution ---
    const durationRanges = [
      { label: '0-1h', min: 0, max: 1 },
      { label: '1-4h', min: 1, max: 4 },
      { label: '4-12h', min: 4, max: 12 },
      { label: '12-24h', min: 12, max: 24 },
      { label: '24h+', min: 24, max: Infinity },
    ]
    const durationData = durationRanges.map(r => {
      const trades = sorted.filter(t => {
        if (!t.opened_at || !t.closed_at) return false
        const hours = (new Date(t.closed_at).getTime() - new Date(t.opened_at).getTime()) / 3600000
        return hours >= r.min && hours < r.max
      })
      const avgPnl = trades.length > 0 ? trades.reduce((s, t) => s + (t.pnl_usd || 0), 0) / trades.length : 0
      return { name: r.label, count: trades.length, avgPnl: parseFloat(avgPnl.toFixed(2)) }
    })

    // --- Summary Stats ---
    const wins = sorted.filter(t => (t.pnl_usd || 0) >= 0)
    const losses = sorted.filter(t => (t.pnl_usd || 0) < 0)
    const totalGross = wins.reduce((s, t) => s + (t.pnl_usd || 0), 0)
    const totalLoss = Math.abs(losses.reduce((s, t) => s + (t.pnl_usd || 0), 0))
    const profitFactor = totalLoss > 0 ? totalGross / totalLoss : totalGross > 0 ? Infinity : 0
    const avgWin = wins.length > 0 ? totalGross / wins.length : 0
    const avgLoss = losses.length > 0 ? totalLoss / losses.length : 0
    const bestTrade = sorted.reduce((best, t) => (t.pnl_usd || 0) > (best.pnl_usd || 0) ? t : best, sorted[0])
    const worstTrade = sorted.reduce((worst, t) => (t.pnl_usd || 0) < (worst.pnl_usd || 0) ? t : worst, sorted[0])

    // Streaks
    let currentStreak = 0, maxWinStreak = 0, maxLossStreak = 0, isWinning = true
    sorted.forEach(t => {
      const isWin = (t.pnl_usd || 0) >= 0
      if (isWin === isWinning) {
        currentStreak++
      } else {
        isWinning = isWin
        currentStreak = 1
      }
      if (isWinning && currentStreak > maxWinStreak) maxWinStreak = currentStreak
      if (!isWinning && currentStreak > maxLossStreak) maxLossStreak = currentStreak
    })

    // Avg Duration
    const durations = sorted.filter(t => t.opened_at && t.closed_at).map(t =>
      (new Date(t.closed_at!).getTime() - new Date(t.opened_at).getTime()) / 3600000
    )
    const avgDuration = durations.length > 0 ? durations.reduce((s, d) => s + d, 0) / durations.length : 0

    // Estimated fees (0.1% per trade round trip)
    const totalFees = sorted.reduce((s, t) => s + (t.size_usd || 0) * 0.001 * 2, 0)

    // ═══ 30-DAY TIMELINE CHARTS ═══
    const now = new Date()
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 3600000)

    // Build daily buckets for last 30 days INCLUDING today
    const dailyMap: Record<string, { date: string; trades: number; wins: number; losses: number; pnl: number; cumPnl: number; volume: number }> = {}
    for (let d = 0; d <= 30; d++) {
      const date = new Date(thirtyDaysAgo.getTime() + d * 24 * 3600000)
      if (date > now) break  // Don't go past today
      const key = date.toISOString().slice(0, 10)
      const label = d === 30 || date.toISOString().slice(0, 10) === now.toISOString().slice(0, 10)
        ? `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')} (auj)`
        : `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}`
      dailyMap[key] = { date: label, trades: 0, wins: 0, losses: 0, pnl: 0, cumPnl: 0, volume: 0 }
    }

    // Fill with closed trades
    sorted.forEach(t => {
      const closedDate = t.closed_at ? t.closed_at.slice(0, 10) : t.opened_at.slice(0, 10)
      if (dailyMap[closedDate]) {
        dailyMap[closedDate].trades += 1
        dailyMap[closedDate].pnl += (t.pnl_usd || 0)
        dailyMap[closedDate].volume += (t.size_usd || 0)
        if ((t.pnl_usd || 0) >= 0) dailyMap[closedDate].wins += 1
        else dailyMap[closedDate].losses += 1
      }
    })

    // Cumulative PnL over 30 days
    const dailyTimeline = Object.values(dailyMap)
    let runningPnl = 0
    dailyTimeline.forEach(d => {
      runningPnl += d.pnl
      d.cumPnl = parseFloat(runningPnl.toFixed(2))
    })

    // Daily WR timeline
    const dailyWr = dailyTimeline.map(d => ({
      date: d.date,
      wr: d.trades > 0 ? parseFloat((d.wins / d.trades * 100).toFixed(1)) : null,
      trades: d.trades,
    }))

    // Daily volume
    const dailyVolume = dailyTimeline.map(d => ({
      date: d.date,
      volume: parseFloat(d.volume.toFixed(0)),
      trades: d.trades,
    }))

    return {
      equityData,
      pnlPerTrade,
      winRateByDecision,
      pnlDistribution,
      decisionPie,
      closeReasonPie,
      topPairs,
      durationData,
      profitFactor,
      avgWin,
      avgLoss,
      maxWinStreak,
      maxLossStreak,
      bestTrade,
      worstTrade,
      avgDuration,
      totalFees,
      dailyTimeline,
      dailyWr,
      dailyVolume,
    }
  }, [history, initialCapital])

  if (!stats) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-12 text-center">
        <Activity className="w-12 h-12 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-500 text-lg">Pas assez de donnees</p>
        <p className="text-gray-600 text-sm mt-1">Les statistiques apparaitront apres la cloture de trades.</p>
      </div>
    )
  }

  const formatDuration = (h: number) => {
    if (h < 1) return `${Math.round(h * 60)}min`
    if (h < 24) return `${h.toFixed(1)}h`
    return `${(h / 24).toFixed(1)}j`
  }

  const renderPieLabel = ({ name, percent }: { name: string; percent: number }) =>
    `${name} (${(percent * 100).toFixed(0)}%)`

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MiniStatCard
          label="Profit Factor"
          value={stats.profitFactor === Infinity ? '∞' : stats.profitFactor.toFixed(2)}
          color={stats.profitFactor >= 1.5 ? 'text-green-400' : stats.profitFactor >= 1 ? 'text-yellow-400' : 'text-red-400'}
        />
        <MiniStatCard
          label="Avg Win / Avg Loss"
          value={`$${stats.avgWin.toFixed(2)} / $${stats.avgLoss.toFixed(2)}`}
          color="text-cyan-400"
        />
        <MiniStatCard
          label="Win Streak / Loss Streak"
          value={`${stats.maxWinStreak}W / ${stats.maxLossStreak}L`}
          color="text-purple-400"
        />
        <MiniStatCard
          label="Meilleur Trade"
          value={`+$${(stats.bestTrade.pnl_usd || 0).toFixed(2)}`}
          color="text-green-400"
        />
        <MiniStatCard
          label="Pire Trade"
          value={`$${(stats.worstTrade.pnl_usd || 0).toFixed(2)}`}
          color="text-red-400"
        />
        <MiniStatCard
          label="Duree Moy / Frais Est."
          value={`${formatDuration(stats.avgDuration)} / $${stats.totalFees.toFixed(2)}`}
          color="text-gray-300"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* 1. Equity Curve */}
        <ChartCard title="Courbe d'Equity">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={stats.equityData}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: COLORS.text }} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} domain={['dataMin - 50', 'dataMax + 50']} />
              <Tooltip content={<CustomTooltip />} />
              <defs>
                <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.green} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.green} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="equity" stroke={COLORS.green} fill="url(#equityGrad)" strokeWidth={2} name="Equity" />
              <Line type="monotone" dataKey="baseline" stroke={COLORS.gray} strokeDasharray="5 5" strokeWidth={1} dot={false} name="Capital Initial" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 2. PnL per Trade */}
        <ChartCard title="PnL par Trade ($)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.pnlPerTrade}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: COLORS.text }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="pnl" name="PnL ($)" radius={[4, 4, 0, 0]}>
                {stats.pnlPerTrade.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 3. Win Rate by Decision */}
        <ChartCard title="Win Rate par Decision">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.winRateByDecision}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: COLORS.text }} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} domain={[0, 100]} unit="%" />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: COLORS.text }} />
              <Bar dataKey="winRate" name="Win %" fill={COLORS.green} radius={[4, 4, 0, 0]} />
              <Bar dataKey="lossRate" name="Loss %" fill={COLORS.red} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2">
            {stats.winRateByDecision.map(d => (
              <span key={d.name} className="text-[10px] text-gray-500">{d.name}: {d.count} trades</span>
            ))}
          </div>
        </ChartCard>

        {/* 4. PnL Distribution */}
        <ChartCard title="Distribution PnL ($)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.pnlDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: COLORS.text }} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} allowDecimals={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="Trades" radius={[4, 4, 0, 0]}>
                {stats.pnlDistribution.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 5. Decision Pie */}
        <ChartCard title="Repartition des Decisions">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={stats.decisionPie}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                label={renderPieLabel}
              >
                {stats.decisionPie.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 6. Close Reason Pie */}
        <ChartCard title="Raisons de Cloture">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={stats.closeReasonPie}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                label={renderPieLabel}
              >
                {stats.closeReasonPie.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 7. Top Pairs Performance */}
        <ChartCard title="Performance par Paire ($)">
          <ResponsiveContainer width="100%" height={Math.max(280, stats.topPairs.length * 30)}>
            <BarChart data={stats.topPairs} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis type="number" tick={{ fontSize: 11, fill: COLORS.text }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: COLORS.text }} width={70} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="pnl" name="PnL ($)" radius={[0, 4, 4, 0]}>
                {stats.topPairs.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 8. Trade Duration Distribution */}
        <ChartCard title="Distribution Duree des Trades">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.durationData}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: COLORS.text }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: COLORS.text }} allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: COLORS.purple }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: COLORS.text }} />
              <Bar yAxisId="left" dataKey="count" name="Trades" fill={COLORS.cyan} radius={[4, 4, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="avgPnl" name="PnL Moy ($)" stroke={COLORS.purple} strokeWidth={2} dot={{ r: 3 }} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

      </div>

      {/* ═══ 30-DAY TIMELINE SECTION ═══ */}
      <h2 className="text-lg font-bold text-gray-200 mt-6 mb-3">📅 Timeline 30 Derniers Jours</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* 9. Daily PnL (30 days) */}
        <ChartCard title="PnL Journalier ($) — 30 jours">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.dailyTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={2} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="pnl" name="PnL $" radius={[3, 3, 0, 0]}>
                {stats.dailyTimeline.map((entry: any, i: number) => (
                  <Cell key={i} fill={entry.pnl >= 0 ? COLORS.green : COLORS.red} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 10. Cumulative PnL (30 days) */}
        <ChartCard title="PnL Cumule ($) — 30 jours">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={stats.dailyTimeline}>
              <defs>
                <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.green} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.green} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={2} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="cumPnl" name="PnL Cumule $" stroke={COLORS.green} fill="url(#cumGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 11. Trades per Day (30 days) */}
        <ChartCard title="Nombre de Trades / Jour — 30 jours">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.dailyTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={2} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} allowDecimals={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: COLORS.text }} />
              <Bar dataKey="wins" name="Wins" stackId="trades" fill={COLORS.green} radius={[0, 0, 0, 0]} />
              <Bar dataKey="losses" name="Losses" stackId="trades" fill={COLORS.red} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 12. Daily Win Rate (30 days) */}
        <ChartCard title="Win Rate Journalier (%) — 30 jours">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={stats.dailyWr.filter((d: any) => d.wr !== null)}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} domain={[0, 100]} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="wr" name="Win Rate %" stroke={COLORS.cyan} strokeWidth={2} dot={{ r: 3, fill: COLORS.cyan }} connectNulls />
              {/* 50% reference line */}
              <Line type="monotone" dataKey={() => 50} name="Seuil 50%" stroke={COLORS.gray} strokeDasharray="5 5" strokeWidth={1} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 13. Daily Volume (30 days) */}
        <ChartCard title="Volume Trade ($) / Jour — 30 jours">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats.dailyVolume}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={2} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="volume" name="Volume $" fill={COLORS.purple} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* 14. Daily Equity Curve (30 days) */}
        <ChartCard title="Equity Journaliere — 30 jours">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={stats.dailyTimeline}>
              <defs>
                <linearGradient id="eqDayGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.cyan} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.cyan} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: COLORS.text }} interval={2} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11, fill: COLORS.text }} domain={['dataMin - 50', 'dataMax + 50']} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="cumPnl" name="Equity $" stroke={COLORS.cyan} fill="url(#eqDayGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

      </div>
    </div>
  )
}

function StatCard({ label, value, sub, icon, color }: { label: string; value: string; sub?: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className={color}>{icon}</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-500">{label}</span>
      </div>
      <div className={cn("text-lg font-bold", color)}>{value}</div>
      {sub && <div className="text-[10px] text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}
