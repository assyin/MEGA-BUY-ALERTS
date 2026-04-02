'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Brain, Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, TrendingUp, TrendingDown, Eye, AlertTriangle, CheckCircle, XCircle, Clock, DollarSign, BarChart3, Filter, X, RefreshCw, FileText, ChevronDown, ChevronUp, Shield, PieChart as PieChartIcon } from 'lucide-react'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import AuditTab from './AuditTab'
import EngagementsTab from './EngagementsTab'
import { supabase } from '@/lib/supabase'
import { cn, formatDate, formatPrice } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────
interface OpenClawDecision {
  id: string
  pair: string
  agent_decision: string // BUY STRONG, BUY, BUY WEAK, WATCH, SKIP
  agent_confidence: number
  outcome: string | null // WIN, LOSE, MISSED_BUY, CORRECT_WATCH, PENDING, null
  pnl_pct: number | null
  pnl_max: number | null
  pnl_min: number | null
  pnl_at_close: number | null
  timestamp: string
  features_fingerprint?: Record<string, any> | null  // lazy-loaded in modal
  analysis_text?: string | null  // lazy-loaded in modal
  alert_id: string | null
  scanner_score: number | null
  chart_path?: string | null  // lazy-loaded in modal
}

interface UsageSummary {
  total_cost_usd: number
  budget_remaining_usd: number
  daily: Record<string, any>
}

interface TimingData {
  analyzed_at: string
  alerts_count: number
  golden_hours: number[]
  best_days: Array<{ day: string; wr_pct: number }>
}

interface Report {
  id: string
  report_type: 'hourly' | 'daily'
  period_start: string
  period_end: string
  content: string
  stats: Record<string, any>
  created_at: string
}

type TabType = 'tracker' | 'stats' | 'hourly' | 'daily' | 'audit' | 'engagements'

const ITEMS_PER_PAGE = 25

// ─── Helper Functions ────────────────────────────────────────
function getDecisionStyle(dec: string) {
  if (dec?.includes('BUY STRONG')) return { color: 'text-green-400', bg: 'bg-green-500/15 border-green-500/30', icon: '🟢🟢', label: 'BUY STRONG' }
  if (dec === 'BUY') return { color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/25', icon: '🟢', label: 'BUY' }
  if (dec?.includes('BUY WEAK')) return { color: 'text-lime-400', bg: 'bg-lime-500/10 border-lime-500/25', icon: '🟡🟢', label: 'BUY WEAK' }
  if (dec === 'WATCH') return { color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/25', icon: '🟡', label: 'WATCH' }
  if (dec === 'SKIP') return { color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/25', icon: '🔴', label: 'SKIP' }
  return { color: 'text-gray-400', bg: 'bg-gray-500/10 border-gray-500/25', icon: '⚪', label: dec || '—' }
}

function getOutcomeStyle(outcome: string | null) {
  if (outcome === 'WIN') return { color: 'text-green-400', bg: 'bg-green-500/15', label: '✅ WIN' }
  if (outcome === 'LOSE') return { color: 'text-red-400', bg: 'bg-red-500/15', label: '❌ LOSE' }
  if (outcome === 'MISSED_BUY') return { color: 'text-orange-400', bg: 'bg-orange-500/15', label: '🚨 MISSED' }
  if (outcome === 'CORRECT_WATCH') return { color: 'text-blue-400', bg: 'bg-blue-500/15', label: '✅ CORRECT' }
  if (outcome === 'PENDING') return { color: 'text-gray-400', bg: 'bg-gray-500/10', label: '⏳ PENDING' }
  return { color: 'text-gray-500', bg: 'bg-gray-500/5', label: '—' }
}

function toGMT1(dateStr: string): string {
  const d = new Date(dateStr)
  d.setHours(d.getHours() + 1)
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" })
}

// ─── Main Component ──────────────────────────────────────────
export default function OpenClawPageClient() {
  const [activeTab, setActiveTab] = useState<TabType>('tracker')
  const [decisions, setDecisions] = useState<OpenClawDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedDecision, setSelectedDecision] = useState<OpenClawDecision | null>(null)
  const [pairSearch, setPairSearch] = useState('')
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL')
  const [outcomeFilter, setOutcomeFilter] = useState<string>('ALL')
  const [vipFilter, setVipFilter] = useState<string>('ALL') // ALL, VIP, HIGH_TICKET, NO_VIP
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [timing, setTiming] = useState<TimingData | null>(null)

  // Advanced filters
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [minConf, setMinConf] = useState('')
  const [maxConf, setMaxConf] = useState('')
  const [minPnl, setMinPnl] = useState('')
  const [maxPnl, setMaxPnl] = useState('')
  const [minScore, setMinScore] = useState('')
  const [minAccum, setMinAccum] = useState('')
  const [gradeFilter, setGradeFilter] = useState<string>('ALL')
  const [maxAccum, setMaxAccum] = useState('')

  // Sort
  const [sortKey, setSortKey] = useState<string>('timestamp')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const toggleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir(key === 'timestamp' ? 'desc' : 'desc')
    }
  }

  const sortIcon = (key: string) => sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''

  // ─── Load Data ───────────────────────────────────────────
  const loadData = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    else setLoading(true)

    try {
      // Load agent_memory — includes features_fingerprint for VIP badge (no analysis_text)
      const { data, error } = await supabase
        .from("agent_memory")
        .select("id,pair,agent_decision,agent_confidence,outcome,pnl_pct,pnl_max,pnl_min,pnl_at_close,timestamp,alert_id,scanner_score,features_fingerprint")
        .order("timestamp", { ascending: false })
        .limit(1000)

      if (!error && data) {
        setDecisions(data)
      }

      // Load usage from OpenClaw API via server-side proxy to avoid CORS
      try {
        const [usageRes, timingRes] = await Promise.all([
          fetch('/api/openclaw/usage').then(r => r.ok ? r.json() : null).catch(() => null),
          fetch('/api/openclaw/timing').then(r => r.ok ? r.json() : null).catch(() => null),
        ])
        if (usageRes) setUsage(usageRes)
        if (timingRes) setTiming(timingRes)
      } catch {}
    } catch (e) {
      console.error('Load error:', e)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // Auto-refresh every 60 seconds for live PnL
  useEffect(() => {
    loadData()
    const interval = setInterval(() => loadData(true), 60000)
    return () => clearInterval(interval)
  }, [])

  // ─── Filtered + Sorted Data ──────────────────────────────
  const filtered = useMemo(() => {
    const result = decisions.filter(d => {
      if (pairSearch && !d.pair?.toLowerCase().includes(pairSearch.toLowerCase())) return false
      if (decisionFilter !== 'ALL' && d.agent_decision !== decisionFilter) return false
      if (outcomeFilter !== 'ALL') {
        if (outcomeFilter === 'PENDING' && d.outcome && d.outcome !== 'PENDING') return false
        if (outcomeFilter !== 'PENDING' && d.outcome !== outcomeFilter) return false
      }
      // Advanced filters
      if (dateFrom && (d.timestamp || '') < dateFrom) return false
      if (dateTo && (d.timestamp || '').slice(0, 10) > dateTo) return false
      if (minConf && (d.agent_confidence || 0) < parseFloat(minConf) / 100) return false
      if (maxConf && (d.agent_confidence || 0) > parseFloat(maxConf) / 100) return false
      if (minPnl && (d.pnl_pct || 0) < parseFloat(minPnl)) return false
      if (maxPnl && (d.pnl_pct || 0) > parseFloat(maxPnl)) return false
      if (minScore && (d.scanner_score || 0) < parseInt(minScore)) return false
      // Accumulation filter
      if (minAccum || maxAccum) {
        const accDays = (d.features_fingerprint || {}).accumulation_days || 0
        if (minAccum && accDays < parseFloat(minAccum)) return false
        if (maxAccum && accDays > parseFloat(maxAccum)) return false
      }
      // Grade filter
      if (gradeFilter !== 'ALL') {
        const grade = (d.features_fingerprint || {}).quality_grade || ''
        if (gradeFilter === 'A+' && grade !== 'A+') return false
        if (gradeFilter === 'A' && grade !== 'A') return false
        if (gradeFilter === '>=A' && grade !== 'A' && grade !== 'A+') return false
        if (gradeFilter === 'B' && grade !== 'B') return false
        if (gradeFilter === 'C' && grade !== 'C' && grade !== '') return false
      }
      // VIP filter
      if (vipFilter !== 'ALL') {
        const fp = d.features_fingerprint || {}
        if (vipFilter === 'VIP' && !fp.is_vip) return false
        if (vipFilter === 'HIGH_TICKET' && !fp.is_high_ticket) return false
        if (vipFilter === 'NO_VIP' && fp.is_vip) return false
      }
      return true
    })

    // Sort
    result.sort((a, b) => {
      let va: any, vb: any
      switch (sortKey) {
        case 'pair': va = a.pair || ''; vb = b.pair || ''; break
        case 'decision': va = a.agent_decision || ''; vb = b.agent_decision || ''; break
        case 'confidence': va = a.agent_confidence || 0; vb = b.agent_confidence || 0; break
        case 'outcome': va = a.outcome || ''; vb = b.outcome || ''; break
        case 'pnl': va = a.pnl_pct || 0; vb = b.pnl_pct || 0; break
        case 'pnl_max': va = a.pnl_max || 0; vb = b.pnl_max || 0; break
        case 'score': va = a.scanner_score || 0; vb = b.scanner_score || 0; break
        default: va = a.timestamp || ''; vb = b.timestamp || ''
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })

    return result
  }, [decisions, pairSearch, decisionFilter, outcomeFilter, vipFilter, gradeFilter, dateFrom, dateTo, minConf, maxConf, minPnl, maxPnl, minScore, minAccum, maxAccum, sortKey, sortDir])

  // ─── Stats ───────────────────────────────────────────────
  const stats = useMemo(() => {
    const total = filtered.length
    const buys = filtered.filter(d => d.agent_decision?.includes('BUY')).length
    const watches = filtered.filter(d => d.agent_decision === 'WATCH').length
    const skips = filtered.filter(d => d.agent_decision === 'SKIP').length

    // WR on resolved trades only
    const withOutcome = filtered.filter(d => d.outcome === 'WIN' || d.outcome === 'LOSE')
    const wins = withOutcome.filter(d => d.outcome === 'WIN').length
    const losses = withOutcome.filter(d => d.outcome === 'LOSE').length
    const wrResolved = withOutcome.length > 0 ? (wins / withOutcome.length * 100) : 0

    // WR LIVE — recalculated on ALL trades with pnl data (more realistic)
    const withPnl = filtered.filter(d => d.pnl_pct !== null && d.pnl_pct !== undefined)
    const liveWins = withPnl.filter(d => (d.pnl_pct || 0) >= 10).length
    const liveLoses = withPnl.filter(d => (d.pnl_pct || 0) <= -8).length
    const wrLive = (liveWins + liveLoses) > 0 ? (liveWins / (liveWins + liveLoses) * 100) : 0

    const pending = filtered.filter(d => !d.outcome || d.outcome === 'PENDING').length
    const missedBuys = filtered.filter(d => d.outcome === 'MISSED_BUY').length
    const correctWatches = filtered.filter(d => d.outcome === 'CORRECT_WATCH').length

    const avgPnl = withOutcome.length > 0
      ? withOutcome.reduce((s, d) => s + (d.pnl_pct || 0), 0) / withOutcome.length
      : 0
    const totalPnl = withOutcome.reduce((s, d) => s + (d.pnl_pct || 0), 0)

    const buyStrong = filtered.filter(d => d.agent_decision?.includes('BUY STRONG')).length
    const buyNormal = filtered.filter(d => d.agent_decision === 'BUY').length
    const buyWeak = filtered.filter(d => d.agent_decision?.includes('BUY WEAK')).length

    return { total, buys, watches, skips, wins, losses, wr: wrResolved, wrLive, pending, missedBuys, correctWatches, avgPnl, totalPnl, buyStrong, buyNormal, buyWeak, withOutcome: withOutcome.length, liveWins, liveLoses }
  }, [filtered])

  // ─── Pagination ──────────────────────────────────────────
  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE)
  const paged = filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)

  useEffect(() => { setCurrentPage(1) }, [pairSearch, decisionFilter, outcomeFilter, vipFilter])

  // ─── Render ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-purple-500/10 rounded-xl">
            <Brain className="w-7 h-7 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-100">OpenClaw Tracker</h1>
            <p className="text-sm text-gray-500">{decisions.length} decisions analysees</p>
          </div>
        </div>
        <button onClick={() => loadData(true)} className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
          <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2">
        {([
          { key: 'tracker' as TabType, label: 'Tracker', icon: <BarChart3 className="w-4 h-4" /> },
          { key: 'stats' as TabType, label: 'Statistiques', icon: <PieChartIcon className="w-4 h-4" /> },
          { key: 'hourly' as TabType, label: 'Rapports Horaires', icon: <Clock className="w-4 h-4" /> },
          { key: 'daily' as TabType, label: 'Rapports Journaliers', icon: <FileText className="w-4 h-4" /> },
          { key: 'audit' as TabType, label: 'Audit', icon: <Shield className="w-4 h-4" /> },
          { key: 'engagements' as TabType, label: 'Engagements', icon: <CheckCircle className="w-4 h-4" /> },
        ]).map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border",
              activeTab === tab.key
                ? "bg-purple-500/20 border-purple-500/40 text-purple-300"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700 hover:text-gray-300"
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'tracker' && (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
            <StatCard label="Total" value={stats.total} icon={<BarChart3 className="w-4 h-4" />} color="text-gray-300" />
            <StatCard label="BUY" value={stats.buys} sub={`S:${stats.buyStrong} N:${stats.buyNormal} W:${stats.buyWeak}`} icon={<CheckCircle className="w-4 h-4" />} color="text-green-400" />
            <StatCard label="WATCH" value={stats.watches} icon={<Eye className="w-4 h-4" />} color="text-yellow-400" />
            <StatCard label="SKIP" value={stats.skips} icon={<XCircle className="w-4 h-4" />} color="text-red-400" />
            <StatCard label="WR Resolus" value={`${stats.wr.toFixed(1)}%`} sub={`${stats.wins}W/${stats.losses}L (${stats.withOutcome} resolus)`} icon={<TrendingUp className="w-4 h-4" />} color={stats.wr >= 60 ? "text-green-400" : stats.wr >= 40 ? "text-yellow-400" : "text-red-400"} />
            <StatCard label="WR Live" value={`${stats.wrLive.toFixed(1)}%`} sub={`${stats.liveWins}W/${stats.liveLoses}L (prix actuel)`} icon={<TrendingUp className="w-4 h-4" />} color={stats.wrLive >= 60 ? "text-green-400" : stats.wrLive >= 40 ? "text-yellow-400" : "text-red-400"} />
            <StatCard label="Pending" value={`${stats.pending}`} sub={`${(stats.pending / Math.max(stats.total, 1) * 100).toFixed(0)}% non-resolus`} icon={<Clock className="w-4 h-4" />} color="text-gray-400" />
            <StatCard label="PnL Total" value={`${stats.totalPnl >= 0 ? '+' : ''}${stats.totalPnl.toFixed(1)}%`} sub={`avg: ${stats.avgPnl >= 0 ? '+' : ''}${stats.avgPnl.toFixed(1)}%`} icon={<DollarSign className="w-4 h-4" />} color={stats.totalPnl >= 0 ? "text-green-400" : "text-red-400"} />
            <StatCard label="Missed BUY" value={stats.missedBuys} icon={<AlertTriangle className="w-4 h-4" />} color="text-orange-400" />
            <StatCard label="Budget" value={usage ? `$${(usage.budget?.remaining_usd ?? usage.budget_remaining_usd)?.toFixed(2)}` : '—'} sub={usage ? `spent: $${(usage.budget?.spent_usd ?? usage.total_cost_usd)?.toFixed(2)}` : ''} icon={<DollarSign className="w-4 h-4" />} color="text-cyan-400" />
          </div>

          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-3 bg-gray-900/50 p-4 rounded-xl border border-gray-800">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Rechercher une paire..."
                value={pairSearch}
                onChange={e => setPairSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Decision Filter */}
            <div className="flex items-center gap-1">
              <Filter className="w-4 h-4 text-gray-500 mr-1" />
              {['ALL', 'BUY STRONG', 'BUY', 'BUY WEAK', 'WATCH', 'SKIP'].map(d => (
                <button
                  key={d}
                  onClick={() => setDecisionFilter(d)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
                    decisionFilter === d
                      ? d === 'ALL' ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                        : getDecisionStyle(d).bg + ' ' + getDecisionStyle(d).color
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
                  )}
                >
                  {d === 'ALL' ? 'Tous' : d}
                </button>
              ))}
            </div>

            {/* Outcome Filter */}
            <div className="flex items-center gap-1">
              {['ALL', 'WIN', 'LOSE', 'MISSED_BUY', 'PENDING'].map(o => (
                <button
                  key={o}
                  onClick={() => setOutcomeFilter(o)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
                    outcomeFilter === o
                      ? o === 'ALL' ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                        : getOutcomeStyle(o).bg + ' border-transparent ' + getOutcomeStyle(o).color
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
                  )}
                >
                  {o === 'ALL' ? 'Tous' : o === 'MISSED_BUY' ? 'Missed' : o}
                </button>
              ))}
            </div>

            {/* VIP Filter */}
            <div className="flex items-center gap-1">
              <span className="text-yellow-500 text-sm mr-0.5">⭐</span>
              {['ALL', 'VIP', 'HIGH_TICKET', 'NO_VIP'].map(v => (
                <button
                  key={v}
                  onClick={() => setVipFilter(v)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
                    vipFilter === v
                      ? v === 'ALL' ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                        : v === 'HIGH_TICKET' ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300'
                        : v === 'VIP' ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                        : 'bg-gray-600/20 border-gray-500/40 text-gray-300'
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
                  )}
                >
                  {v === 'ALL' ? 'Tous' : v === 'HIGH_TICKET' ? '🏆 HT' : v === 'VIP' ? '⭐ VIP' : 'No VIP'}
                </button>
              ))}
            </div>

            {(pairSearch || decisionFilter !== 'ALL' || outcomeFilter !== 'ALL' || vipFilter !== 'ALL') && (
              <button
                onClick={() => { setPairSearch(''); setDecisionFilter('ALL'); setOutcomeFilter('ALL'); setVipFilter('ALL'); setGradeFilter('ALL'); setDateFrom(''); setDateTo(''); setMinConf(''); setMaxConf(''); setMinPnl(''); setMaxPnl(''); setMinScore(''); setMinAccum(''); setMaxAccum('') }}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-gray-400 hover:text-gray-200 bg-gray-800 border border-gray-700 hover:bg-gray-700"
              >
                <X className="w-3 h-3" /> Reset
              </button>
            )}

            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                showAdvanced ? "bg-purple-500/20 border-purple-500/40 text-purple-300" : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700"
              )}
            >
              {showAdvanced ? '▼ Filtres avances' : '▶ Filtres avances'}
            </button>

            <span className="text-xs text-gray-500 ml-auto">{filtered.length} resultats</span>
          </div>

          {/* Advanced Filters Panel */}
          {showAdvanced && (
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-9 gap-3">
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Date debut</label>
                <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Date fin</label>
                <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Conf min %</label>
                <input type="number" placeholder="0" value={minConf} onChange={e => setMinConf(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Conf max %</label>
                <input type="number" placeholder="100" value={maxConf} onChange={e => setMaxConf(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">PnL min %</label>
                <input type="number" placeholder="-100" value={minPnl} onChange={e => setMinPnl(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">PnL max %</label>
                <input type="number" placeholder="100" value={maxPnl} onChange={e => setMaxPnl(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Score min</label>
                <input type="number" placeholder="0" min="0" max="10" value={minScore} onChange={e => setMinScore(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Accum min (j)</label>
                <input type="number" placeholder="0" step="0.5" min="0" value={minAccum} onChange={e => setMinAccum(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Accum max (j)</label>
                <input type="number" placeholder="30" step="0.5" min="0" value={maxAccum} onChange={e => setMaxAccum(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Grade Qualite</label>
                <div className="flex gap-1 mt-1">
                  {['ALL', 'A+', 'A', '>=A', 'B', 'C'].map(g => (
                    <button key={g} onClick={() => setGradeFilter(g)}
                      className={cn("px-2 py-1 rounded text-xs font-medium border transition-colors",
                        gradeFilter === g
                          ? g === 'ALL' ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                            : g === 'A+' ? 'bg-green-500/20 border-green-500/40 text-green-300 font-bold'
                            : g === 'A' || g === '>=A' ? 'bg-green-500/15 border-green-500/30 text-green-300'
                            : g === 'B' ? 'bg-yellow-500/15 border-yellow-500/30 text-yellow-300'
                            : 'bg-gray-600/20 border-gray-500/30 text-gray-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>
                      {g === 'ALL' ? 'Tous' : g}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                    <th className="px-4 py-3 text-left cursor-pointer hover:text-gray-200" onClick={() => toggleSort('timestamp')}>Date{sortIcon('timestamp')}</th>
                    <th className="px-4 py-3 text-left cursor-pointer hover:text-gray-200" onClick={() => toggleSort('pair')}>Paire{sortIcon('pair')}</th>
                    <th className="px-4 py-3 text-center">VIP</th>
                    <th className="px-4 py-3 text-center">Accum</th>
                    <th className="px-4 py-3 text-center cursor-pointer hover:text-gray-200" onClick={() => toggleSort('score')}>Score{sortIcon('score')}</th>
                    <th className="px-4 py-3 text-center cursor-pointer hover:text-gray-200" onClick={() => toggleSort('decision')}>Decision{sortIcon('decision')}</th>
                    <th className="px-4 py-3 text-center">Grade</th>
                    <th className="px-4 py-3 text-center cursor-pointer hover:text-gray-200" onClick={() => toggleSort('confidence')}>Confiance{sortIcon('confidence')}</th>
                    <th className="px-4 py-3 text-center cursor-pointer hover:text-gray-200" onClick={() => toggleSort('outcome')}>Outcome{sortIcon('outcome')}</th>
                    <th className="px-4 py-3 text-right cursor-pointer hover:text-gray-200" onClick={() => toggleSort('pnl')}>PnL Live{sortIcon('pnl')}</th>
                    <th className="px-4 py-3 text-right cursor-pointer hover:text-gray-200" onClick={() => toggleSort('pnl_max')}>PnL Max{sortIcon('pnl_max')}</th>
                    <th className="px-4 py-3 text-center">Chart</th>
                    <th className="px-4 py-3 text-center">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {paged.map((d) => {
                    const decStyle = getDecisionStyle(d.agent_decision)
                    const outStyle = getOutcomeStyle(d.outcome)
                    return (
                      <tr
                        key={d.id}
                        className="border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors cursor-pointer"
                        onClick={() => setSelectedDecision(d)}
                      >
                        <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                          {d.timestamp ? toGMT1(d.timestamp) : '—'}
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-200">
                          <a
                            href={`https://www.tradingview.com/chart/?symbol=BINANCE%3A${d.pair}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-purple-400 transition-colors"
                            onClick={e => e.stopPropagation()}
                          >
                            {d.pair?.replace('USDT', '')}
                            <span className="text-gray-600 font-normal">USDT</span>
                            <span className="text-[10px] ml-1 text-gray-600">↗</span>
                          </a>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {(() => {
                            const fp = d.features_fingerprint || {}
                            if (fp.is_high_ticket) return <span title={`VIP ${fp.vip_score}/5 — High Ticket`} className="text-base cursor-help">🏆</span>
                            if (fp.is_vip) return <span title={`VIP ${fp.vip_score}/5`} className="text-base cursor-help">⭐</span>
                            return <span className="text-gray-700 text-xs">—</span>
                          })()}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {(() => {
                            const fp = d.features_fingerprint || {}
                            const days = fp.accumulation_days
                            if (!days || days <= 0) return <span className="text-gray-700 text-xs">—</span>
                            const color = days >= 5 ? 'text-green-400' : days >= 3 ? 'text-yellow-400' : 'text-gray-400'
                            return <span className={`${color} text-xs font-medium cursor-help`} title={`Range: ${fp.accumulation_range_pct || '?'}%`}>{days.toFixed(1)}j</span>
                          })()}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {d.scanner_score ? (
                            <span className={cn("font-bold", d.scanner_score >= 8 ? 'text-green-400' : d.scanner_score >= 6 ? 'text-yellow-400' : 'text-red-400')}>
                              {d.scanner_score}/10
                            </span>
                          ) : (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={cn("px-2.5 py-1 rounded-full text-xs font-medium border", decStyle.bg, decStyle.color)}>
                            {decStyle.icon} {decStyle.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {(() => {
                            const fp = d.features_fingerprint || {}
                            const grade = fp.quality_grade
                            const axes = fp.quality_axes || 0
                            if (!grade) return <span className="text-gray-700 text-xs">—</span>
                            const color = grade === 'A+' ? 'text-green-400 font-bold' : grade === 'A' ? 'text-green-400' : grade === 'B' ? 'text-yellow-400' : 'text-gray-500'
                            const details = (fp.quality_details || []).join(', ')
                            return <span className={`${color} text-xs cursor-help`} title={details || `${axes}/4 axes`}>{grade}</span>
                          })()}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            <div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                              <div
                                className={cn("h-full rounded-full", d.agent_confidence >= 0.7 ? 'bg-green-500' : d.agent_confidence >= 0.5 ? 'bg-yellow-500' : 'bg-red-500')}
                                style={{ width: `${(d.agent_confidence || 0) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-400">{((d.agent_confidence || 0) * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={cn("px-2 py-0.5 rounded text-xs font-medium", outStyle.bg, outStyle.color)}>
                            {outStyle.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {d.pnl_pct !== null && d.pnl_pct !== undefined ? (
                            <span className={cn("font-mono font-medium", d.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400')}>
                              {d.pnl_pct >= 0 ? '+' : ''}{d.pnl_pct.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {d.pnl_max !== null && d.pnl_max !== undefined ? (
                            <span className={cn("font-mono text-xs", (d.pnl_max || 0) >= 0 ? 'text-green-400/70' : 'text-red-400/70')}>
                              {(d.pnl_max || 0) >= 0 ? '+' : ''}{(d.pnl_max || 0).toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-gray-600 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {d.chart_path ? (
                            <span className="text-green-400 text-xs">📊</span>
                          ) : (
                            <span className="text-gray-600 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button className="text-purple-400 hover:text-purple-300 text-xs underline">
                            Voir
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                  {paged.length === 0 && (
                    <tr>
                      <td colSpan={13} className="px-4 py-12 text-center text-gray-500">
                        Aucune decision trouvee
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
                <span className="text-xs text-gray-500">
                  Page {currentPage}/{totalPages} — {filtered.length} resultats
                </span>
                <div className="flex items-center gap-1">
                  <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronsLeft className="w-4 h-4 text-gray-400" /></button>
                  <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronLeft className="w-4 h-4 text-gray-400" /></button>
                  <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronRight className="w-4 h-4 text-gray-400" /></button>
                  <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronsRight className="w-4 h-4 text-gray-400" /></button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === 'stats' && <TrackerStatsTab decisions={decisions} />}
      {activeTab === 'hourly' && <ReportsTab reportType="hourly" />}
      {activeTab === 'daily' && <ReportsTab reportType="daily" />}
      {activeTab === 'audit' && <AuditTab />}
      {activeTab === 'engagements' && <EngagementsTab />}

      {/* Detail Modal */}
      {selectedDecision && (
        <DecisionModal
          decision={selectedDecision}
          onClose={() => setSelectedDecision(null)}
        />
      )}
    </div>
  )
}

// ─── Colors ──────────────────────────────────────────────────
const DECISION_COLORS: Record<string, string> = {
  'BUY STRONG': '#16a34a',
  'BUY': '#4ade80',
  'BUY WEAK': '#a3e635',
  'WATCH': '#fbbf24',
  'SKIP': '#f87171',
}
const OUTCOME_COLORS: Record<string, string> = {
  'WIN': '#4ade80',
  'LOSE': '#f87171',
  'MISSED_BUY': '#fb923c',
  'CORRECT_WATCH': '#60a5fa',
  'PENDING': '#6b7280',
}

// ─── Custom Tooltip ──────────────────────────────────────────
function DarkTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 shadow-xl">
      {label && <p className="text-xs text-gray-400 mb-1">{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} className="text-xs font-medium" style={{ color: p.color || p.fill || '#9ca3af' }}>
          {p.name}: {typeof p.value === 'number' ? (Number.isInteger(p.value) ? p.value : p.value.toFixed(1)) : p.value}
          {p.name?.includes('%') || p.dataKey?.includes('wr') || p.dataKey?.includes('pnl') ? '%' : ''}
        </p>
      ))}
    </div>
  )
}

// ─── Tracker Stats Tab ───────────────────────────────────────
function TrackerStatsTab({ decisions }: { decisions: OpenClawDecision[] }) {
  // ── Summary stats ──
  const summary = useMemo(() => {
    const total = decisions.length
    const buyCount = decisions.filter(d => d.agent_decision?.includes('BUY')).length
    const watchCount = decisions.filter(d => d.agent_decision === 'WATCH').length
    const skipCount = decisions.filter(d => d.agent_decision === 'SKIP').length
    const resolved = decisions.filter(d => d.outcome === 'WIN' || d.outcome === 'LOSE')
    const wins = resolved.filter(d => d.outcome === 'WIN').length
    const wr = resolved.length > 0 ? (wins / resolved.length * 100) : 0
    const missedCount = decisions.filter(d => d.outcome === 'MISSED_BUY').length
    const pnls = resolved.filter(d => d.pnl_pct != null).map(d => d.pnl_pct!)
    const avgPnl = pnls.length > 0 ? pnls.reduce((a, b) => a + b, 0) / pnls.length : 0
    const bestPnl = pnls.length > 0 ? Math.max(...pnls) : 0
    const worstPnl = pnls.length > 0 ? Math.min(...pnls) : 0
    return { total, buyCount, watchCount, skipCount, wr, missedCount, avgPnl, bestPnl, worstPnl, resolvedCount: resolved.length }
  }, [decisions])

  // ── 1. Decision distribution pie ──
  const decisionPieData = useMemo(() => {
    const counts: Record<string, number> = {}
    decisions.forEach(d => {
      const key = d.agent_decision?.includes('BUY STRONG') ? 'BUY STRONG'
        : d.agent_decision?.includes('BUY WEAK') ? 'BUY WEAK'
        : d.agent_decision === 'BUY' ? 'BUY'
        : d.agent_decision === 'WATCH' ? 'WATCH'
        : d.agent_decision === 'SKIP' ? 'SKIP'
        : 'OTHER'
      counts[key] = (counts[key] || 0) + 1
    })
    return Object.entries(counts)
      .filter(([k]) => k !== 'OTHER')
      .map(([name, value]) => ({ name, value }))
  }, [decisions])

  // ── 2. Outcome distribution pie ──
  const outcomePieData = useMemo(() => {
    const counts: Record<string, number> = {}
    decisions.forEach(d => {
      const key = d.outcome || 'PENDING'
      counts[key] = (counts[key] || 0) + 1
    })
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [decisions])

  // ── 3. WR by decision type ──
  const wrByType = useMemo(() => {
    const types = ['BUY STRONG', 'BUY', 'BUY WEAK', 'WATCH', 'SKIP']
    return types.map(type => {
      const matching = decisions.filter(d => {
        if (type === 'BUY STRONG') return d.agent_decision?.includes('BUY STRONG')
        if (type === 'BUY WEAK') return d.agent_decision?.includes('BUY WEAK')
        if (type === 'BUY') return d.agent_decision === 'BUY'
        return d.agent_decision === type
      })
      const resolved = matching.filter(d => d.outcome === 'WIN' || d.outcome === 'LOSE')
      const wins = resolved.filter(d => d.outcome === 'WIN').length
      const wr = resolved.length > 0 ? (wins / resolved.length * 100) : 0
      return { type, wr: Math.round(wr * 10) / 10, count: resolved.length, fill: DECISION_COLORS[type] || '#6b7280' }
    })
  }, [decisions])

  // ── 4. PnL by decision type ──
  const pnlByType = useMemo(() => {
    const types = ['BUY STRONG', 'BUY', 'BUY WEAK', 'WATCH', 'SKIP']
    return types.map(type => {
      const matching = decisions.filter(d => {
        if (type === 'BUY STRONG') return d.agent_decision?.includes('BUY STRONG')
        if (type === 'BUY WEAK') return d.agent_decision?.includes('BUY WEAK')
        if (type === 'BUY') return d.agent_decision === 'BUY'
        return d.agent_decision === type
      })
      const withPnl = matching.filter(d => d.pnl_pct != null && (d.outcome === 'WIN' || d.outcome === 'LOSE'))
      const avg = withPnl.length > 0 ? withPnl.reduce((s, d) => s + (d.pnl_pct || 0), 0) / withPnl.length : 0
      return { type, avgPnl: Math.round(avg * 100) / 100, count: withPnl.length, fill: DECISION_COLORS[type] || '#6b7280' }
    })
  }, [decisions])

  // ── Helper: get last 30 days ──
  const last30Days = useMemo(() => {
    const days: string[] = []
    const today = new Date()
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      days.push(d.toISOString().slice(0, 10))
    }
    return days
  }, [])

  // ── 5. Daily decisions count (stacked) ──
  const dailyDecisions = useMemo(() => {
    const todayStr = new Date().toISOString().slice(0, 10)
    const byDay: Record<string, Record<string, number>> = {}
    last30Days.forEach(day => { byDay[day] = { 'BUY STRONG': 0, 'BUY': 0, 'BUY WEAK': 0, 'WATCH': 0, 'SKIP': 0 } })
    decisions.forEach(d => {
      if (!d.timestamp) return
      const day = d.timestamp.slice(0, 10)
      if (!byDay[day]) return
      const key = d.agent_decision?.includes('BUY STRONG') ? 'BUY STRONG'
        : d.agent_decision?.includes('BUY WEAK') ? 'BUY WEAK'
        : d.agent_decision === 'BUY' ? 'BUY'
        : d.agent_decision === 'WATCH' ? 'WATCH'
        : d.agent_decision === 'SKIP' ? 'SKIP'
        : null
      if (key && byDay[day]) byDay[day][key]++
    })
    return last30Days.map(day => ({
      date: day === todayStr ? `${day.slice(5)} (auj)` : day.slice(5),
      ...byDay[day],
    }))
  }, [decisions, last30Days])

  // ── 6. Daily PnL ──
  const dailyPnl = useMemo(() => {
    const todayStr = new Date().toISOString().slice(0, 10)
    const byDay: Record<string, number> = {}
    last30Days.forEach(day => { byDay[day] = 0 })
    decisions.forEach(d => {
      if (!d.timestamp || d.pnl_pct == null) return
      if (d.outcome !== 'WIN' && d.outcome !== 'LOSE') return
      const day = d.timestamp.slice(0, 10)
      if (byDay[day] !== undefined) byDay[day] += d.pnl_pct
    })
    return last30Days.map(day => ({
      date: day === todayStr ? `${day.slice(5)} (auj)` : day.slice(5),
      pnl: Math.round(byDay[day] * 100) / 100,
    }))
  }, [decisions, last30Days])

  // ── 7. Confidence distribution ──
  const confidenceDist = useMemo(() => {
    const ranges = [
      { label: '0-30%', min: 0, max: 0.3 },
      { label: '30-50%', min: 0.3, max: 0.5 },
      { label: '50-60%', min: 0.5, max: 0.6 },
      { label: '60-70%', min: 0.6, max: 0.7 },
      { label: '70-80%', min: 0.7, max: 0.8 },
      { label: '80%+', min: 0.8, max: 1.01 },
    ]
    return ranges.map(r => {
      const inRange = decisions.filter(d => (d.agent_confidence || 0) >= r.min && (d.agent_confidence || 0) < r.max)
      const resolved = inRange.filter(d => d.outcome === 'WIN' || d.outcome === 'LOSE')
      const wins = resolved.filter(d => d.outcome === 'WIN').length
      const wr = resolved.length > 0 ? Math.round((wins / resolved.length) * 1000) / 10 : 0
      return { range: r.label, count: inRange.length, wr }
    })
  }, [decisions])

  // ── 8. Top pairs by frequency ──
  const topPairs = useMemo(() => {
    const counts: Record<string, number> = {}
    decisions.forEach(d => {
      if (d.pair) counts[d.pair] = (counts[d.pair] || 0) + 1
    })
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([pair, count]) => ({ pair: pair.replace('USDT', ''), count }))
  }, [decisions])

  // ── 9. Missed BUY analysis ──
  const missedBuys = useMemo(() => {
    return decisions
      .filter(d => d.outcome === 'MISSED_BUY' && d.pnl_pct != null)
      .sort((a, b) => (b.pnl_pct || 0) - (a.pnl_pct || 0))
      .slice(0, 10)
      .map(d => ({
        pair: (d.pair || '').replace('USDT', ''),
        missedPnl: d.pnl_pct || 0,
      }))
  }, [decisions])

  // ── 10. WR timeline (rolling 7-day) ──
  const wrTimeline = useMemo(() => {
    const todayStr = new Date().toISOString().slice(0, 10)
    return last30Days.map(day => {
      const dayDate = new Date(day)
      const weekAgo = new Date(dayDate)
      weekAgo.setDate(weekAgo.getDate() - 7)
      const weekAgoStr = weekAgo.toISOString().slice(0, 10)

      const inWindow = decisions.filter(d => {
        if (!d.timestamp) return false
        const dDay = d.timestamp.slice(0, 10)
        return dDay > weekAgoStr && dDay <= day
      })
      const resolved = inWindow.filter(d => d.outcome === 'WIN' || d.outcome === 'LOSE')
      const wins = resolved.filter(d => d.outcome === 'WIN').length
      const wr = resolved.length >= 3 ? Math.round((wins / resolved.length) * 1000) / 10 : null
      return {
        date: day === todayStr ? `${day.slice(5)} (auj)` : day.slice(5),
        wr,
      }
    })
  }, [decisions, last30Days])

  // ── Empty state ──
  if (decisions.length === 0) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-12 text-center">
        <BarChart3 className="w-10 h-10 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-400">Pas assez de donnees</p>
        <p className="text-gray-500 text-xs mt-2">Les statistiques apparaitront quand OpenClaw aura analyse des alertes</p>
      </div>
    )
  }

  const chartBox = "bg-gray-900/60 border border-gray-800 rounded-xl p-4"

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <StatCard label="Total" value={summary.total} icon={<BarChart3 className="w-4 h-4" />} color="text-gray-300" />
        <StatCard label="BUY" value={summary.buyCount} icon={<CheckCircle className="w-4 h-4" />} color="text-green-400" />
        <StatCard label="WATCH" value={summary.watchCount} icon={<Eye className="w-4 h-4" />} color="text-yellow-400" />
        <StatCard label="SKIP" value={summary.skipCount} icon={<XCircle className="w-4 h-4" />} color="text-red-400" />
        <StatCard label="Win Rate" value={`${summary.wr.toFixed(1)}%`} sub={`sur ${summary.resolvedCount} resolues`} icon={<TrendingUp className="w-4 h-4" />} color={summary.wr >= 60 ? "text-green-400" : summary.wr >= 40 ? "text-yellow-400" : "text-red-400"} />
        <StatCard label="Missed BUY" value={summary.missedCount} icon={<AlertTriangle className="w-4 h-4" />} color="text-orange-400" />
        <StatCard label="PnL Moyen" value={`${summary.avgPnl >= 0 ? '+' : ''}${summary.avgPnl.toFixed(1)}%`} icon={<DollarSign className="w-4 h-4" />} color={summary.avgPnl >= 0 ? "text-green-400" : "text-red-400"} />
        <StatCard label="Best / Worst" value={`+${summary.bestPnl.toFixed(1)}%`} sub={`${summary.worstPnl.toFixed(1)}%`} icon={<TrendingDown className="w-4 h-4" />} color="text-cyan-400" />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Decision Distribution Pie */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Distribution des Decisions</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={decisionPieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {decisionPieData.map((entry, i) => (
                  <Cell key={i} fill={DECISION_COLORS[entry.name] || '#6b7280'} />
                ))}
              </Pie>
              <Tooltip content={<DarkTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 2. Outcome Distribution Pie */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Distribution des Outcomes</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={outcomePieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {outcomePieData.map((entry, i) => (
                  <Cell key={i} fill={OUTCOME_COLORS[entry.name] || '#6b7280'} />
                ))}
              </Pie>
              <Tooltip content={<DarkTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 3. WR by Decision Type */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Win Rate par Type de Decision</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={wrByType}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} domain={[0, 100]} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="wr" name="WR%" radius={[4, 4, 0, 0]}>
                {wrByType.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 4. PnL by Decision Type */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">PnL Moyen par Type de Decision</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={pnlByType}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="avgPnl" name="PnL Moy%" radius={[4, 4, 0, 0]}>
                {pnlByType.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 5. Daily Decisions Count (stacked) */}
        <div className={cn(chartBox, "md:col-span-2")}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Decisions par Jour (30 jours)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={dailyDecisions}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <Tooltip content={<DarkTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
              <Bar dataKey="BUY STRONG" stackId="a" fill="#16a34a" />
              <Bar dataKey="BUY" stackId="a" fill="#4ade80" />
              <Bar dataKey="BUY WEAK" stackId="a" fill="#a3e635" />
              <Bar dataKey="WATCH" stackId="a" fill="#fbbf24" />
              <Bar dataKey="SKIP" stackId="a" fill="#f87171" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 6. Daily PnL */}
        <div className={cn(chartBox, "md:col-span-2")}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">PnL Quotidien (30 jours)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={dailyPnl}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="pnl" name="PnL%" radius={[3, 3, 0, 0]}>
                {dailyPnl.map((entry, i) => (
                  <Cell key={i} fill={entry.pnl >= 0 ? '#4ade80' : '#f87171'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 7. Confidence Distribution */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Distribution de Confiance + WR</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={confidenceDist}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="range" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 11 }} domain={[0, 100]} />
              <Tooltip content={<DarkTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
              <Bar yAxisId="left" dataKey="count" name="Nombre" fill="#6366f1" radius={[3, 3, 0, 0]} />
              <Bar yAxisId="right" dataKey="wr" name="WR%" fill="#4ade80" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 8. Top Pairs by Frequency */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Top Paires Analysees</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={topPairs} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="pair" tick={{ fill: '#9ca3af', fontSize: 11 }} width={70} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" name="Analyses" fill="#a78bfa" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 9. Missed BUY Analysis */}
        <div className={chartBox}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Missed BUY — PnL Manque</h3>
          {missedBuys.length === 0 ? (
            <div className="flex items-center justify-center h-[280px] text-gray-500 text-sm">
              <div className="text-center">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-gray-600" />
                <p>Aucun Missed BUY avec PnL</p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={missedBuys} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis type="category" dataKey="pair" tick={{ fill: '#9ca3af', fontSize: 11 }} width={70} />
                <Tooltip content={<DarkTooltip />} />
                <Bar dataKey="missedPnl" name="PnL Manque%" fill="#fb923c" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* 10. WR Timeline (rolling 7-day) */}
        <div className={cn(chartBox, "md:col-span-2")}>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Win Rate Glissant 7 Jours</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={wrTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} domain={[0, 100]} />
              <Tooltip content={<DarkTooltip />} />
              <Line type="monotone" dataKey="wr" name="WR% (7j)" stroke="#a78bfa" strokeWidth={2} dot={{ r: 2, fill: '#a78bfa' }} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ─── Reports Tab Component ──────────────────────────────────
function ReportsTab({ reportType }: { reportType: 'hourly' | 'daily' }) {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genResult, setGenResult] = useState<string | null>(null)

  const handleGenerate = async () => {
    setGenerating(true)
    setGenResult(null)
    try {
      const res = await fetch('/api/openclaw/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: reportType }),
      })
      const data = await res.json()
      if (data.status === 'ok') {
        setGenResult(data.message)
        // Reload reports after 2s to let Supabase sync
        setTimeout(() => loadReports(), 2000)
      } else {
        setGenResult(`Erreur: ${data.error || 'Unknown'}`)
      }
    } catch {
      setGenResult('Erreur: OpenClaw unreachable')
    } finally {
      setGenerating(false)
    }
  }

  const loadReports = useCallback(async () => {
    try {
      const res = await fetch(`/api/openclaw/reports?type=${reportType}&limit=50`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (data.error) {
        setError(data.error)
        setReports([])
      } else {
        setReports(data.reports || [])
        setError(null)
      }
    } catch (e: any) {
      setError(e.message || 'Erreur de connexion')
      setReports([])
    } finally {
      setLoading(false)
    }
  }, [reportType])

  useEffect(() => {
    setLoading(true)
    loadReports()
    const interval = setInterval(loadReports, 60000)
    return () => clearInterval(interval)
  }, [loadReports])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-yellow-400 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">{error}</p>
        <p className="text-gray-500 text-xs mt-2">Verifiez que OpenClaw est en cours d'execution sur le port 8002</p>
      </div>
    )
  }

  // Generate button component (reused in empty state and header)
  const GenerateButton = () => (
    <button
      onClick={handleGenerate}
      disabled={generating}
      className={cn(
        "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
        generating
          ? "bg-gray-700 text-gray-500 cursor-wait"
          : "bg-purple-500/20 border border-purple-500/40 text-purple-300 hover:bg-purple-500/30"
      )}
    >
      <RefreshCw className={cn("w-4 h-4", generating && "animate-spin")} />
      {generating ? 'Generation en cours...' : `Generer ${reportType === 'hourly' ? 'rapport horaire' : 'rapport journalier'}`}
    </button>
  )

  if (reports.length === 0) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-12 text-center">
        <FileText className="w-10 h-10 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-400">Aucun rapport {reportType === 'hourly' ? 'horaire' : 'journalier'} disponible</p>
        <p className="text-gray-500 text-xs mt-2 mb-4">Les rapports seront generes automatiquement</p>
        <GenerateButton />
        {genResult && (
          <p className={cn("mt-3 text-sm", genResult.includes('Erreur') ? "text-red-400" : "text-green-400")}>{genResult}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Generate button + result message */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{reports.length} rapport(s)</span>
        <div className="flex items-center gap-3">
          {genResult && (
            <span className={cn("text-sm", genResult.includes('Erreur') ? "text-red-400" : "text-green-400")}>{genResult}</span>
          )}
          <GenerateButton />
        </div>
      </div>

      {reports.map(report => (
        <ReportCard
          key={report.id}
          report={report}
          expanded={expandedId === report.id}
          onToggle={() => setExpandedId(expandedId === report.id ? null : report.id)}
        />
      ))}
    </div>
  )
}

// ─── Report Card Component ──────────────────────────────────
function ReportCard({ report, expanded, onToggle }: { report: Report; expanded: boolean; onToggle: () => void }) {
  const stats = report.stats || {}
  const periodStart = toGMT1(report.period_start)
  const periodEnd = toGMT1(report.period_end)

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-800/30 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            "p-2 rounded-lg",
            report.report_type === 'hourly' ? "bg-cyan-500/10" : "bg-purple-500/10"
          )}>
            {report.report_type === 'hourly'
              ? <Clock className="w-4 h-4 text-cyan-400" />
              : <FileText className="w-4 h-4 text-purple-400" />
            }
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-200">
                {periodStart} — {periodEnd}
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {report.report_type === 'hourly' ? 'Rapport Horaire' : 'Rapport Journalier'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Stats Badges */}
          <div className="flex items-center gap-2">
            {stats.decisions_count !== undefined && (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-800 border border-gray-700 text-gray-300">
                {stats.decisions_count || stats.buy_count + stats.watch_count + stats.skip_count || 0} decisions
              </span>
            )}
            {(stats.wr_pct !== undefined && stats.wr_pct > 0) && (
              <span className={cn(
                "px-2 py-0.5 rounded text-[10px] font-medium",
                stats.wr_pct >= 60 ? "bg-green-500/15 text-green-400" : stats.wr_pct >= 40 ? "bg-yellow-500/15 text-yellow-400" : "bg-red-500/15 text-red-400"
              )}>
                WR {stats.wr_pct}%
              </span>
            )}
            {stats.insights_count > 0 && (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/15 text-blue-400">
                {stats.insights_count} insights
              </span>
            )}
            {(stats.total_pnl !== undefined && stats.total_pnl !== 0) && (
              <span className={cn(
                "px-2 py-0.5 rounded text-[10px] font-mono font-medium",
                stats.total_pnl >= 0 ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400"
              )}>
                {stats.total_pnl >= 0 ? '+' : ''}{stats.total_pnl}%
              </span>
            )}
          </div>

          {expanded
            ? <ChevronUp className="w-4 h-4 text-gray-500" />
            : <ChevronDown className="w-4 h-4 text-gray-500" />
          }
        </div>
      </button>

      {/* Body — expanded */}
      {expanded && (
        <div className="border-t border-gray-800 p-4 space-y-4">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {stats.alerts_count !== undefined && (
              <MiniStat label="Alertes" value={stats.alerts_count} />
            )}
            {stats.buy_count !== undefined && (
              <MiniStat label="BUY" value={stats.buy_count} color="text-green-400" />
            )}
            {stats.watch_count !== undefined && (
              <MiniStat label="WATCH" value={stats.watch_count} color="text-yellow-400" />
            )}
            {stats.skip_count !== undefined && (
              <MiniStat label="SKIP" value={stats.skip_count} color="text-red-400" />
            )}
            {stats.missed_buys !== undefined && stats.missed_buys > 0 && (
              <MiniStat label="Missed" value={stats.missed_buys} color="text-orange-400" />
            )}
            {stats.insights_count !== undefined && (
              <MiniStat label="Insights" value={stats.insights_count} color="text-blue-400" />
            )}
          </div>

          {/* Full Content */}
          <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 max-h-[500px] overflow-y-auto">
            <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
              {report.content || 'Contenu non disponible'}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Mini Stat for Report Card ──────────────────────────────
function MiniStat({ label, value, color = "text-gray-300" }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2">
      <div className="text-[10px] text-gray-500 uppercase">{label}</div>
      <div className={cn("text-sm font-bold", color)}>{value}</div>
    </div>
  )
}

// ─── Stat Card Component ─────────────────────────────────────
function StatCard({ label, value, sub, icon, color }: { label: string; value: string | number; sub?: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className={color}>{icon}</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-500">{label}</span>
      </div>
      <div className={cn("text-xl font-bold", color)}>{value}</div>
      {sub && <div className="text-[10px] text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}

// ─── Decision Detail Modal ───────────────────────────────────
function DecisionModal({ decision, onClose }: { decision: OpenClawDecision; onClose: () => void }) {
  const decStyle = getDecisionStyle(decision.agent_decision)
  const outStyle = getOutcomeStyle(decision.outcome)
  const [features, setFeatures] = useState<Record<string, any>>(decision.features_fingerprint || {})
  const [chartUrl, setChartUrl] = useState<string | null>(null)
  const [chartLoading, setChartLoading] = useState(false)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [reanalyzeResult, setReanalyzeResult] = useState<string | null>(null)
  const [analysisText, setAnalysisText] = useState<string | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(true)

  // Lazy-load analysis_text + features from Supabase when modal opens
  useEffect(() => {
    const loadDetails = async () => {
      setLoadingAnalysis(true)
      try {
        const { data } = await supabase
          .from("agent_memory")
          .select("analysis_text,features_fingerprint,chart_path")
          .eq("id", decision.id)
          .single()
        setAnalysisText(data?.analysis_text || null)
        if (data?.features_fingerprint) {
          setFeatures(data.features_fingerprint)
        }
      } catch {}
      setLoadingAnalysis(false)
    }
    loadDetails()
  }, [decision.id])

  // Regenerate analysis
  const handleReanalyze = async () => {
    setReanalyzing(true)
    setReanalyzeResult(null)
    try {
      const res = await fetch('/api/openclaw/reanalyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ memory_id: decision.id }),
      })
      const data = await res.json()
      if (data.status === 'ok') {
        setReanalyzeResult(`Re-analyse OK — ${data.decision} (${(data.confidence * 100).toFixed(0)}%) — Telegram envoye`)
        // Reload the decision data to get new analysis
        try {
          const { data: updated } = await supabase
            .from('agent_memory')
            .select('*')
            .eq('id', decision.id)
            .single()
          if (updated?.analysis_text) {
            setAnalysisText(updated.analysis_text)
          }
        } catch {}
      } else {
        setReanalyzeResult(`Erreur: ${data.error || 'Unknown'}`)
      }
    } catch (e) {
      setReanalyzeResult('Erreur: OpenClaw unreachable')
    } finally {
      setReanalyzing(false)
    }
  }

  // Load chart image — try by alert_id first, then by pair name
  useEffect(() => {
    const loadChart = async () => {
      setChartLoading(true)
      setChartUrl(null)

      // Try 1: by alert_id via API proxy
      if (decision.alert_id) {
        try {
          const url = `/api/openclaw/chart?alert_id=${decision.alert_id}`
          const r = await fetch(url)
          if (r.ok && r.headers.get('content-type')?.includes('image')) {
            setChartUrl(url)
            setChartLoading(false)
            return
          }
        } catch {}
      }

      // Try 2: by pair name directly from OpenClaw
      if (decision.pair) {
        try {
          const url = `/api/openclaw/chart?pair=${decision.pair}`
          const r = await fetch(url)
          if (r.ok && r.headers.get('content-type')?.includes('image')) {
            setChartUrl(url)
            setChartLoading(false)
            return
          }
        } catch {}
      }

      setChartLoading(false)
    }
    loadChart()
  }, [decision.alert_id, decision.pair])

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div className="flex items-center gap-4">
            <div className="flex flex-col">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-gray-100">{decision.pair?.replace('USDT', '')}<span className="text-gray-500 font-normal">USDT</span></span>
                <span className={cn("px-3 py-1 rounded-full text-sm font-medium border", decStyle.bg, decStyle.color)}>
                  {decStyle.icon} {decStyle.label}
                </span>
                {decision.outcome && (
                  <span className={cn("px-3 py-1 rounded-full text-sm font-medium", outStyle.bg, outStyle.color)}>
                    {outStyle.label}
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-500 mt-1">
                {decision.timestamp ? toGMT1(decision.timestamp) : ''} — Confiance: {((decision.agent_confidence || 0) * 100).toFixed(0)}%
                {decision.pnl_pct !== null && decision.pnl_pct !== undefined && (
                  <span className={cn("ml-3 font-mono font-medium", decision.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400')}>
                    PnL: {decision.pnl_pct >= 0 ? '+' : ''}{decision.pnl_pct.toFixed(2)}%
                  </span>
                )}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Alert Info */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Donnees de l'Alerte</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <InfoBox label="Score" value={features.scanner_score ? `${features.scanner_score}/10` : '—'} />
              <InfoBox label="Prix" value={features.price ? formatPrice(features.price) : '—'} />
              <InfoBox label="Timeframes" value={features.timeframes?.join(', ') || '—'} />
              <InfoBox label="DI+ 4H" value={features.di_plus_4h?.toFixed(1) || '—'} />
              <InfoBox label="DI- 4H" value={features.di_minus_4h?.toFixed(1) || '—'} />
              <InfoBox label="ADX 4H" value={features.adx_4h?.toFixed(1) || '—'} />
              <InfoBox label="PP" value={features.pp ? '✅' : '❌'} />
              <InfoBox label="EC" value={features.ec ? '✅' : '❌'} />
            </div>
          </div>

          {/* Chart Image */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Graphique Technique</h3>
            {chartLoading ? (
              <div className="bg-gray-950 border border-gray-800 rounded-xl p-8 flex items-center justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500" />
              </div>
            ) : chartUrl ? (
              <div className="bg-gray-950 border border-gray-800 rounded-xl overflow-hidden">
                <img
                  src={chartUrl}
                  alt={`Chart ${decision.pair}`}
                  className="w-full h-auto"
                  onError={() => setChartUrl(null)}
                />
              </div>
            ) : (
              <div className="bg-gray-950 border border-gray-800 rounded-xl p-6 text-center text-gray-500 text-sm">
                Chart non disponible
              </div>
            )}
          </div>

          {/* Full Analysis Text */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Analyse Complete OpenClaw</h3>
              <button
                onClick={handleReanalyze}
                disabled={reanalyzing}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                  reanalyzing
                    ? "bg-gray-700 text-gray-500 cursor-wait"
                    : "bg-purple-500/20 border border-purple-500/40 text-purple-300 hover:bg-purple-500/30"
                )}
              >
                <RefreshCw className={cn("w-4 h-4", reanalyzing && "animate-spin")} />
                {reanalyzing ? 'Re-analyse en cours...' : 'Regenerer + Telegram'}
              </button>
            </div>
            {reanalyzeResult && (
              <div className={cn(
                "mb-3 px-4 py-2 rounded-lg text-sm",
                reanalyzeResult.includes('OK') ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
              )}>
                {reanalyzeResult}
              </div>
            )}
            <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 max-h-[400px] overflow-y-auto">
              {loadingAnalysis ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500" />
                  <span className="ml-3 text-gray-500 text-sm">Chargement de l'analyse...</span>
                </div>
              ) : analysisText ? (
                <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {analysisText}
                </pre>
              ) : (
                <p className="text-gray-500 text-sm italic">Analyse non disponible — cliquez sur "Regenerer" pour lancer l'analyse</p>
              )}
            </div>
          </div>

          {/* Features Fingerprint */}
          {features && Object.keys(features).length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Features Techniques</h3>
              <div className="bg-gray-950 border border-gray-800 rounded-xl p-4 max-h-[200px] overflow-y-auto">
                <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono">
                  {JSON.stringify(features, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Info Box ────────────────────────────────────────────────
function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2">
      <div className="text-[10px] text-gray-500 uppercase">{label}</div>
      <div className="text-sm text-gray-200 font-medium">{value}</div>
    </div>
  )
}
