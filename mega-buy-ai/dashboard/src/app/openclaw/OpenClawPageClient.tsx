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
  chart_path?: string | null
  outcome_at?: string | null
  pnl_max_at?: string | null  // lazy-loaded in modal
  // Merged from alerts table
  alert_data?: Record<string, any> | null
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

const PAGE_SIZE_OPTIONS = [25, 50, 100, 500] as const

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
  // Force UTC+1 display regardless of browser timezone
  const utc1 = new Date(d.getTime() + 1 * 3600000)
  const dd = String(utc1.getUTCDate()).padStart(2, '0')
  const mm = String(utc1.getUTCMonth() + 1).padStart(2, '0')
  const yy = String(utc1.getUTCFullYear()).slice(-2)
  const hh = String(utc1.getUTCHours()).padStart(2, '0')
  const mn = String(utc1.getUTCMinutes()).padStart(2, '0')
  return `${dd}/${mm}/${yy} ${hh}:${mn}`
}

// ─── Main Component ──────────────────────────────────────────
export default function OpenClawPageClient() {
  const ALL_COLUMNS = [
    { key: 'date', label: 'Date', default: true },
    { key: 'pair', label: 'Paire', default: true },
    { key: 'vip', label: 'VIP', default: true },
    { key: 'tfs', label: 'TFs', default: true },
    { key: 'score', label: 'Score', default: true },
    { key: 'di_plus', label: 'DI+', default: true },
    { key: 'di_minus', label: 'DI-', default: true },
    { key: 'adx', label: 'ADX', default: true },
    { key: 'di_spread', label: 'D±', default: true },
    { key: 'rsi', label: 'RSI', default: true },
    { key: 'change24h', label: '24h%', default: true },
    { key: 'body4h', label: 'Body', default: true },
    { key: 'range4h', label: 'Range', default: true },
    { key: 'vol_1h', label: 'V1h', default: true },
    { key: 'vol_4h', label: 'V4h', default: true },
    { key: 'vol_24h', label: 'V24h', default: true },
    { key: 'vol_48h', label: 'V48h', default: true },
    { key: 'stc_15m', label: 'STC15', default: true },
    { key: 'stc_30m', label: 'STC30', default: true },
    { key: 'stc_1h', label: 'STC1h', default: true },
    { key: 'tf_body', label: 'TFBody', default: true },
    { key: 'fg', label: 'F&G', default: true },
    { key: 'btc', label: 'BTC', default: true },
    { key: 'eth', label: 'ETH', default: true },
    { key: 'pp', label: 'PP', default: false },
    { key: 'ec', label: 'EC', default: false },
    { key: 'accum', label: 'Accum', default: true },
    { key: 'decision', label: 'Decision', default: true },
    { key: 'grade', label: 'Grade', default: false },
    { key: 'confidence', label: 'Conf', default: true },
    { key: 'outcome', label: 'Outcome', default: true },
    { key: 'pnl', label: 'PnL', default: true },
    { key: 'pnl_max', label: 'Max', default: true },
    { key: 'tv', label: 'TV', default: false },
  ] as const
  const [visibleCols, setVisibleCols] = useState<Set<string>>(() => new Set(ALL_COLUMNS.filter(c => c.default).map(c => c.key)))
  const [showColPicker, setShowColPicker] = useState(false)
  const col = (key: string) => visibleCols.has(key)
  const toggleCol = (key: string) => setVisibleCols(prev => { const s = new Set(prev); s.has(key) ? s.delete(key) : s.add(key); return s })

  const [activeTab, setActiveTab] = useState<TabType>('tracker')
  const [decisions, setDecisions] = useState<OpenClawDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [perPage, setPerPage] = useState(25)
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
  const [gradeFilter, setGradeFilter] = useState<string[]>([]) // empty = ALL, can contain multiple
  const [maxAccum, setMaxAccum] = useState('')
  const [minDiPlus, setMinDiPlus] = useState('')
  const [maxDiPlus, setMaxDiPlus] = useState('')
  const [minDiMinus, setMinDiMinus] = useState('')
  const [maxDiMinus, setMaxDiMinus] = useState('')
  const [minAdx, setMinAdx] = useState('')
  const [maxAdx, setMaxAdx] = useState('')
  const [minRsi, setMinRsi] = useState('')
  const [maxRsi, setMaxRsi] = useState('')
  const [ppFilter, setPpFilter] = useState<string>('ALL')
  const [ecFilter, setEcFilter] = useState<string>('ALL')
  const [tfFilter, setTfFilter] = useState<string[]>([]) // empty = ALL, can contain multiple TFs
  const [minPuissance, setMinPuissance] = useState('')
  const [minVolPct, setMinVolPct] = useState('')
  const [maxVolPct, setMaxVolPct] = useState('')
  const [condFilters, setCondFilters] = useState<string[]>([]) // RSI,DMI,AST,CHoCH,Zone,Lazy,Vol,ST
  const [minChange24h, setMinChange24h] = useState('')
  const [maxChange24h, setMaxChange24h] = useState('')
  const [minBody4h, setMinBody4h] = useState('')
  const [maxBody4h, setMaxBody4h] = useState('')
  const [minRange4h, setMinRange4h] = useState('')
  const [maxRange4h, setMaxRange4h] = useState('')
  const [dirFilter, setDirFilter] = useState<string>('ALL') // ALL, green, red
  // Market sentiment filters
  const [fgFilter, setFgFilter] = useState<string[]>([]) // Extreme Fear, Fear, Neutral, Greed, Extreme Greed
  const [btcTrendFilter, setBtcTrendFilter] = useState<string>('ALL') // ALL, BULLISH, BEARISH
  const [ethTrendFilter, setEthTrendFilter] = useState<string>('ALL')
  const [altSeasonFilter, setAltSeasonFilter] = useState<string>('ALL') // ALL, YES, NO
  // Volume spike filters
  const [minVol1h, setMinVol1h] = useState('')
  const [minVol4h, setMinVol4h] = useState('')
  const [minVol24h, setMinVol24h] = useState('')
  const [minVol48h, setMinVol48h] = useState('')
  // DI Spread filter
  const [minDiSpread, setMinDiSpread] = useState('')
  const [maxDiSpread, setMaxDiSpread] = useState('')
  // STC filters
  const [maxStc15m, setMaxStc15m] = useState('')
  const [maxStc30m, setMaxStc30m] = useState('')
  const [maxStc1h, setMaxStc1h] = useState('')
  // TF body filter
  const [minTfBody, setMinTfBody] = useState('')
  // V8/V9 All preset (union of Ultra + Vol bypass)
  const [v8v9AllMode, setV8v9AllMode] = useState(false)

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
      // Load agent_memory — always last 30 days, paginated
      const since30d = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10)
      const fields = "id,pair,agent_decision,agent_confidence,outcome,pnl_pct,pnl_max,pnl_min,pnl_at_close,timestamp,alert_id,scanner_score,features_fingerprint,outcome_at,pnl_max_at"
      let allRows: any[] = []
      let page = 0
      const PG = 1000
      while (true) {
        const { data: batch } = await supabase
          .from("agent_memory")
          .select(fields)
          .gte("timestamp", since30d + "T00:00:00")
          .order("timestamp", { ascending: false })
          .range(page * PG, (page + 1) * PG - 1)
        if (!batch || batch.length === 0) break
        allRows = allRows.concat(batch)
        if (batch.length < PG) break
        page++
      }
      const data = allRows
      const error = null

      if (!error && data) {
        // Load alert data for enrichment (conditions, puissance, lazy, vol_pct, etc.)
        const alertIds = data.filter(d => d.alert_id).map(d => d.alert_id!)
        let alertsMap: Record<string, any> = {}
        if (alertIds.length > 0) {
          // Batch load in chunks of 100
          for (let i = 0; i < alertIds.length; i += 100) {
            const chunk = alertIds.slice(i, i + 100)
            const { data: alertData } = await supabase
              .from("alerts")
              .select("id,alert_timestamp,rsi_check,dmi_check,ast_check,choch,zone,lazy,vol,st,puissance,vol_pct,lazy_values,ec_moves,emotion,rsi_moves,nb_timeframes")
              .in("id", chunk)
            if (alertData) {
              for (const a of alertData) {
                alertsMap[a.id] = a
              }
            }
          }
        }
        // Merge alert data into decisions
        const enriched = data.map(d => ({
          ...d,
          alert_data: d.alert_id ? (alertsMap[d.alert_id] || null) : null,
        }))
        setDecisions(enriched)
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
      // Compare dates in GMT+1 (displayed timezone)
      if (dateFrom || dateTo) {
        const dt = new Date(d.timestamp || '')
        dt.setHours(dt.getHours() + 1) // GMT+1
        const displayDate = dt.toISOString().slice(0, 10)
        if (dateFrom && displayDate < dateFrom) return false
        if (dateTo && displayDate > dateTo) return false
      }
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
      if (gradeFilter.length > 0) {
        const grade = (d.features_fingerprint || {}).quality_grade || ''
        // Pass if grade matches any of the selected filters
        let pass = false
        for (const gf of gradeFilter) {
          if (gf === 'A+' && grade === 'A+') pass = true
          else if (gf === 'A' && grade === 'A') pass = true
          else if (gf === '>=A' && (grade === 'A' || grade === 'A+')) pass = true
          else if (gf === 'B' && grade === 'B') pass = true
          else if (gf === 'C' && (grade === 'C' || grade === '')) pass = true
        }
        if (!pass) return false
      }
      // VIP filter
      if (vipFilter !== 'ALL') {
        const fp = d.features_fingerprint || {}
        if (vipFilter === 'VIP' && !fp.is_vip) return false
        if (vipFilter === 'HIGH_TICKET' && !fp.is_high_ticket) return false
        if (vipFilter === 'NO_VIP' && fp.is_vip) return false
      }
      // DI+/DI-/ADX/RSI filters
      const fp2 = d.features_fingerprint || {}
      if (minDiPlus && (fp2.di_plus_4h || 0) < parseFloat(minDiPlus)) return false
      if (maxDiPlus && (fp2.di_plus_4h || 0) > parseFloat(maxDiPlus)) return false
      if (minDiMinus && (fp2.di_minus_4h || 0) < parseFloat(minDiMinus)) return false
      if (maxDiMinus && (fp2.di_minus_4h || 0) > parseFloat(maxDiMinus)) return false
      if (minAdx && (fp2.adx_4h || 0) < parseFloat(minAdx)) return false
      if (maxAdx && (fp2.adx_4h || 0) > parseFloat(maxAdx)) return false
      if (minRsi && (fp2.rsi || 0) < parseFloat(minRsi)) return false
      if (maxRsi && (fp2.rsi || 0) > parseFloat(maxRsi)) return false
      // PP/EC filter
      if (ppFilter === 'YES' && !fp2.pp) return false
      if (ppFilter === 'NO' && fp2.pp) return false
      if (ecFilter === 'YES' && !fp2.ec) return false
      if (ecFilter === 'NO' && fp2.ec) return false
      // Timeframe filter (multi-select OR logic + multi keyword for 2+ TFs)
      if (tfFilter.length > 0) {
        const tfs = fp2.timeframes || []
        const hasMulti = tfFilter.includes('multi')
        const tfList = tfFilter.filter(t => t !== 'multi')
        // If only "multi" selected → must have 2+ TFs
        // If specific TFs selected → must include at least one of them
        // If both → must satisfy at least one condition
        let pass = false
        if (hasMulti && tfs.length >= 2) pass = true
        if (tfList.length > 0 && tfList.some(t => tfs.includes(t))) pass = true
        if (!pass) return false
      }
      // Alert-based filters (from alerts table)
      const ad = (d as any).alert_data || {}
      if (minPuissance && (ad.puissance || 0) < parseInt(minPuissance)) return false
      // Vol% filter (max vol across TFs)
      if (minVolPct || maxVolPct) {
        const volObj = ad.vol_pct || {}
        const maxVol = typeof volObj === 'object' ? Math.max(0, ...Object.values(volObj).map((v: any) => Number(v) || 0)) : 0
        if (minVolPct && maxVol < parseFloat(minVolPct)) return false
        if (maxVolPct && maxVol > parseFloat(maxVolPct)) return false
      }
      // Conditions filter (all required)
      if (condFilters.length > 0) {
        const condMap: Record<string, string> = { RSI: 'rsi_check', DMI: 'dmi_check', AST: 'ast_check', CHoCH: 'choch', Zone: 'zone', Lazy: 'lazy', Vol: 'vol', ST: 'st' }
        for (const cf of condFilters) {
          if (!ad[condMap[cf]]) return false
        }
      }
      // 24h change filter
      if (minChange24h || maxChange24h) {
        const ch = fp2.change_24h_pct
        if (ch == null) return false
        if (minChange24h && ch < parseFloat(minChange24h)) return false
        if (maxChange24h && ch > parseFloat(maxChange24h)) return false
      }
      // 4H Body filter
      if (minBody4h || maxBody4h) {
        const bo = fp2.candle_4h_body_pct
        if (bo == null) return false
        if (minBody4h && bo < parseFloat(minBody4h)) return false
        if (maxBody4h && bo > parseFloat(maxBody4h)) return false
      }
      // 4H Range filter
      if (minRange4h || maxRange4h) {
        const ra = fp2.candle_4h_range_pct
        if (ra == null) return false
        if (minRange4h && ra < parseFloat(minRange4h)) return false
        if (maxRange4h && ra > parseFloat(maxRange4h)) return false
      }
      // 4H Direction filter
      if (dirFilter !== 'ALL') {
        const di = fp2.candle_4h_direction
        if (di !== dirFilter) return false
      }
      // Market sentiment filters
      if (fgFilter.length > 0) {
        const fg = fp2.fear_greed_label
        if (!fg || !fgFilter.includes(fg)) return false
      }
      if (btcTrendFilter !== 'ALL') {
        if (fp2.btc_trend_1h !== btcTrendFilter) return false
      }
      if (ethTrendFilter !== 'ALL') {
        if (fp2.eth_trend_1h !== ethTrendFilter) return false
      }
      if (altSeasonFilter !== 'ALL') {
        const alt = fp2.alt_season
        if (alt == null) return false
        if (altSeasonFilter === 'YES' && !alt) return false
        if (altSeasonFilter === 'NO' && alt) return false
      }
      // Volume spike filters
      if (minVol1h && (fp2.vol_spike_vs_1h == null || fp2.vol_spike_vs_1h < parseFloat(minVol1h))) return false
      if (minVol4h && (fp2.vol_spike_vs_4h == null || fp2.vol_spike_vs_4h < parseFloat(minVol4h))) return false
      if (minVol24h && (fp2.vol_spike_vs_24h == null || fp2.vol_spike_vs_24h < parseFloat(minVol24h))) return false
      if (minVol48h && (fp2.vol_spike_vs_48h == null || fp2.vol_spike_vs_48h < parseFloat(minVol48h))) return false
      // TF body filter — get the max body across alert TFs
      if (minTfBody) {
        const tfs2 = fp2.timeframes || []
        const tfBodyMax = Math.max(0, ...tfs2.map((tf: string) => fp2[`candle_${tf}_body_pct`] ?? 0))
        if (tfBodyMax < parseFloat(minTfBody)) return false
      }
      // STC filters (max = oversold threshold, lower = more oversold)
      if (maxStc15m && (fp2.stc_15m == null || fp2.stc_15m > parseFloat(maxStc15m))) return false
      if (maxStc30m && (fp2.stc_30m == null || fp2.stc_30m > parseFloat(maxStc30m))) return false
      if (maxStc1h && (fp2.stc_1h == null || fp2.stc_1h > parseFloat(maxStc1h))) return false
      // DI Spread filter (DI+ - DI-)
      if (minDiSpread || maxDiSpread) {
        const diP = fp2.di_plus_4h; const diM = fp2.di_minus_4h
        if (diP == null || diM == null) return false
        const spread = diP - diM
        if (minDiSpread && spread < parseFloat(minDiSpread)) return false
        if (maxDiSpread && spread > parseFloat(maxDiSpread)) return false
      }
      // V8/V9 All mode — union of Ultra (ADX 15-35, DI+<=45) OR Vol bypass (Vol>=200%, ADX 15-40, DI+<=65)
      if (v8v9AllMode) {
        const body = fp2.candle_4h_body_pct ?? 0
        const rng = fp2.candle_4h_range_pct ?? 0
        const dir = fp2.candle_4h_direction
        const dip = fp2.di_plus_4h ?? 0
        const adxv = fp2.adx_4h ?? 0
        const ppv = fp2.pp
        const ecv = fp2.ec
        const ch = fp2.change_24h_pct ?? 0
        const btcv = fp2.btc_trend_1h
        const ethv = fp2.eth_trend_1h
        const vol24 = fp2.vol_spike_vs_24h ?? 0
        const baseGate = body >= 3 && rng >= 3.5 && dir === 'green' && adxv <= 50 && ppv && ecv && ch >= 0 && ch <= 50 && btcv === 'BULLISH' && ethv === 'BULLISH'
        const stc15v = fp2.stc_15m ?? -1
        const stc30v = fp2.stc_30m ?? -1
        const stc1hv = fp2.stc_1h ?? 999
        const stcOk = (stc15v < 0 || stc15v < 0.99) && (stc1hv >= 0.1 || stc1hv > 900)
        const v1h = fp2.vol_spike_vs_1h ?? null; const v4h = fp2.vol_spike_vs_4h ?? null; const v24hv = fp2.vol_spike_vs_24h ?? null; const v48h = fp2.vol_spike_vs_48h ?? null
        const allVolNeg = v1h !== null && v4h !== null && v24hv !== null && v48h !== null && v1h < 0 && v4h < 0 && v24hv < 0 && v48h < 0
        const volOk = !allVolNeg
        const dim = fp2.di_minus_4h ?? 0
        const diSpread = dip - dim
        const spreadOk = diSpread < 50
        const confOk = (d.agent_confidence ?? 0) >= 0.60
        const ultra = baseGate && dip <= 45 && adxv >= 15 && adxv < 35 && ch >= 1 && stcOk && volOk && spreadOk && confOk
        const volBp = body >= 3 && rng >= 3.5 && dir === 'green' && adxv <= 50 && ppv && ecv && ch >= 1 && ch <= 50 && btcv === 'BULLISH' && dip <= 65 && adxv >= 15 && adxv < 40 && vol24 >= 200 && stcOk && volOk && spreadOk && confOk
        if (!ultra && !volBp) return false
      }
      return true
    })

    // Sort
    result.sort((a, b) => {
      let va: any, vb: any
      const fp_a = a.features_fingerprint || {}
      const fp_b = b.features_fingerprint || {}
      switch (sortKey) {
        case 'pair': va = a.pair || ''; vb = b.pair || ''; break
        case 'decision': va = a.agent_decision || ''; vb = b.agent_decision || ''; break
        case 'confidence': va = a.agent_confidence || 0; vb = b.agent_confidence || 0; break
        case 'outcome': va = a.outcome || ''; vb = b.outcome || ''; break
        case 'pnl': va = a.pnl_pct || 0; vb = b.pnl_pct || 0; break
        case 'pnl_max': va = a.pnl_max || 0; vb = b.pnl_max || 0; break
        case 'score': va = a.scanner_score || 0; vb = b.scanner_score || 0; break
        case 'vip': va = fp_a.is_high_ticket ? 2 : fp_a.is_vip ? 1 : 0; vb = fp_b.is_high_ticket ? 2 : fp_b.is_vip ? 1 : 0; break
        case 'tfs': va = (fp_a.timeframes || []).length; vb = (fp_b.timeframes || []).length; break
        case 'di_plus': va = fp_a.di_plus_4h || 0; vb = fp_b.di_plus_4h || 0; break
        case 'di_minus': va = fp_a.di_minus_4h || 0; vb = fp_b.di_minus_4h || 0; break
        case 'adx': va = fp_a.adx_4h || 0; vb = fp_b.adx_4h || 0; break
        case 'rsi': va = fp_a.rsi || 0; vb = fp_b.rsi || 0; break
        case 'change24h': va = fp_a.change_24h_pct || 0; vb = fp_b.change_24h_pct || 0; break
        case 'body4h': va = fp_a.candle_4h_body_pct || 0; vb = fp_b.candle_4h_body_pct || 0; break
        case 'range4h': va = fp_a.candle_4h_range_pct || 0; vb = fp_b.candle_4h_range_pct || 0; break
        case 'di_spread': va = (fp_a.di_plus_4h || 0) - (fp_a.di_minus_4h || 0); vb = (fp_b.di_plus_4h || 0) - (fp_b.di_minus_4h || 0); break
        case 'vol_1h': va = fp_a.vol_spike_vs_1h || 0; vb = fp_b.vol_spike_vs_1h || 0; break
        case 'vol_4h': va = fp_a.vol_spike_vs_4h || 0; vb = fp_b.vol_spike_vs_4h || 0; break
        case 'vol_24h': va = fp_a.vol_spike_vs_24h || 0; vb = fp_b.vol_spike_vs_24h || 0; break
        case 'vol_48h': va = fp_a.vol_spike_vs_48h || 0; vb = fp_b.vol_spike_vs_48h || 0; break
        case 'stc_15m': va = fp_a.stc_15m ?? 999; vb = fp_b.stc_15m ?? 999; break
        case 'stc_30m': va = fp_a.stc_30m ?? 999; vb = fp_b.stc_30m ?? 999; break
        case 'stc_1h': va = fp_a.stc_1h ?? 999; vb = fp_b.stc_1h ?? 999; break
        case 'tf_body': {
          const tfsA = fp_a.timeframes || []; const tfsB = fp_b.timeframes || []
          va = Math.max(0, ...tfsA.map((tf: string) => fp_a[`candle_${tf}_body_pct`] ?? 0))
          vb = Math.max(0, ...tfsB.map((tf: string) => fp_b[`candle_${tf}_body_pct`] ?? 0))
          break
        }
        case 'fg': va = fp_a.fear_greed_value || 0; vb = fp_b.fear_greed_value || 0; break
        case 'pp': va = fp_a.pp ? 1 : 0; vb = fp_b.pp ? 1 : 0; break
        case 'ec': va = fp_a.ec ? 1 : 0; vb = fp_b.ec ? 1 : 0; break
        case 'accum': va = fp_a.accumulation_days || 0; vb = fp_b.accumulation_days || 0; break
        case 'grade': va = fp_a.quality_grade === 'A+' ? 4 : fp_a.quality_grade === 'A' ? 3 : fp_a.quality_grade === 'B' ? 2 : fp_a.quality_grade === 'C' ? 1 : 0; vb = fp_b.quality_grade === 'A+' ? 4 : fp_b.quality_grade === 'A' ? 3 : fp_b.quality_grade === 'B' ? 2 : fp_b.quality_grade === 'C' ? 1 : 0; break
        default: va = a.timestamp || ''; vb = b.timestamp || ''
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })

    return result
  }, [decisions, pairSearch, decisionFilter, outcomeFilter, vipFilter, gradeFilter, dateFrom, dateTo, minConf, maxConf, minPnl, maxPnl, minScore, minAccum, maxAccum, minDiPlus, maxDiPlus, minDiMinus, maxDiMinus, minAdx, maxAdx, minRsi, maxRsi, ppFilter, ecFilter, tfFilter, minPuissance, minVolPct, maxVolPct, condFilters, minChange24h, maxChange24h, minBody4h, maxBody4h, minRange4h, maxRange4h, dirFilter, fgFilter, btcTrendFilter, ethTrendFilter, altSeasonFilter, minVol1h, minVol4h, minVol24h, minVol48h, maxStc15m, maxStc30m, maxStc1h, minTfBody, minDiSpread, maxDiSpread, v8v9AllMode, sortKey, sortDir])

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
  const totalPages = Math.ceil(filtered.length / perPage)
  const paged = filtered.slice((currentPage - 1) * perPage, currentPage * perPage)

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
    <div className="px-3 py-4 space-y-4 w-full">
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
                onClick={() => { setPairSearch(''); setDecisionFilter('ALL'); setOutcomeFilter('ALL'); setVipFilter('ALL'); setGradeFilter([]); setDateFrom(''); setDateTo(''); setMinConf(''); setMaxConf(''); setMinPnl(''); setMaxPnl(''); setMinScore(''); setMinAccum(''); setMaxAccum(''); setMinDiPlus(''); setMaxDiPlus(''); setMinDiMinus(''); setMaxDiMinus(''); setMinAdx(''); setMaxAdx(''); setMinRsi(''); setMaxRsi(''); setPpFilter('ALL'); setEcFilter('ALL'); setTfFilter([]); setMinPuissance(''); setMinVolPct(''); setMaxVolPct(''); setCondFilters([]); setMinChange24h(''); setMaxChange24h(''); setMinBody4h(''); setMaxBody4h(''); setMinRange4h(''); setMaxRange4h(''); setDirFilter('ALL'); setFgFilter([]); setBtcTrendFilter('ALL'); setEthTrendFilter('ALL'); setAltSeasonFilter('ALL'); setMinVol1h(''); setMinVol4h(''); setMinVol24h(''); setMinVol48h(''); setMinDiSpread(''); setMaxDiSpread(''); setMaxStc15m(''); setMaxStc30m(''); setMaxStc1h(''); setMinTfBody(''); setV8v9AllMode(false) }}
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

          </div>

          {/* Advanced Filters Panel */}
          {showAdvanced && (<>
            {/* Row 2: DI+, DI-, ADX, RSI, Puissance, Vol% */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-10 gap-3">
              <div>
                <label className="text-[10px] text-gray-500 uppercase">DI+ min</label>
                <input type="number" placeholder="0" value={minDiPlus} onChange={e => setMinDiPlus(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">DI+ max</label>
                <input type="number" placeholder="100" value={maxDiPlus} onChange={e => setMaxDiPlus(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">DI- min</label>
                <input type="number" placeholder="0" value={minDiMinus} onChange={e => setMinDiMinus(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">DI- max</label>
                <input type="number" placeholder="100" value={maxDiMinus} onChange={e => setMaxDiMinus(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">ADX min</label>
                <input type="number" placeholder="0" value={minAdx} onChange={e => setMinAdx(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">ADX max</label>
                <input type="number" placeholder="100" value={maxAdx} onChange={e => setMaxAdx(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">RSI min</label>
                <input type="number" placeholder="0" value={minRsi} onChange={e => setMinRsi(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">RSI max</label>
                <input type="number" placeholder="100" value={maxRsi} onChange={e => setMaxRsi(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Puissance ≥</label>
                <input type="number" placeholder="0" value={minPuissance} onChange={e => setMinPuissance(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol% min</label>
                <input type="number" placeholder="0" value={minVolPct} onChange={e => setMinVolPct(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">24h% min</label>
                <input type="number" placeholder="-100" value={minChange24h} onChange={e => setMinChange24h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">24h% max</label>
                <input type="number" placeholder="100" value={maxChange24h} onChange={e => setMaxChange24h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
            </div>
            {/* Row 2bis: 4H Body / Range / Direction */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Body 4H min %</label>
                <input type="number" placeholder="0" value={minBody4h} onChange={e => setMinBody4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Body 4H max %</label>
                <input type="number" placeholder="100" value={maxBody4h} onChange={e => setMaxBody4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Range 4H min %</label>
                <input type="number" placeholder="0" value={minRange4h} onChange={e => setMinRange4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Range 4H max %</label>
                <input type="number" placeholder="100" value={maxRange4h} onChange={e => setMaxRange4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">DI Spread min</label>
                <input type="number" placeholder="-50" value={minDiSpread} onChange={e => setMinDiSpread(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">DI Spread max</label>
                <input type="number" placeholder="80" value={maxDiSpread} onChange={e => setMaxDiSpread(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 1H min %</label>
                <input type="number" placeholder="-100" value={minVol1h} onChange={e => setMinVol1h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 4H min %</label>
                <input type="number" placeholder="-100" value={minVol4h} onChange={e => setMinVol4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 24H min %</label>
                <input type="number" placeholder="-100" value={minVol24h} onChange={e => setMinVol24h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 48H min %</label>
                <input type="number" placeholder="-100" value={minVol48h} onChange={e => setMinVol48h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">TF Body min %</label>
                <input type="number" step="0.5" placeholder="0" value={minTfBody} onChange={e => setMinTfBody(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">STC 15m max</label>
                <input type="number" step="0.1" placeholder="1" value={maxStc15m} onChange={e => setMaxStc15m(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">STC 30m max</label>
                <input type="number" step="0.1" placeholder="1" value={maxStc30m} onChange={e => setMaxStc30m(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">STC 1h max</label>
                <input type="number" step="0.1" placeholder="1" value={maxStc1h} onChange={e => setMaxStc1h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Direction 4H</label>
                <div className="flex gap-1 mt-1">
                  {['ALL', 'green', 'red'].map(v => (
                    <button key={v} onClick={() => setDirFilter(v)}
                      className={cn("px-2 py-1 rounded text-xs font-medium border transition-colors",
                        dirFilter === v
                          ? v === 'green' ? 'bg-green-500/20 border-green-500/40 text-green-300'
                            : v === 'red' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                            : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>
                      {v === 'ALL' ? '—' : v === 'green' ? '🟢' : '🔴'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            {/* Row 2ter: Market Sentiment */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="md:col-span-2">
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">Fear & Greed (multi)</label>
                <div className="flex gap-1 flex-wrap">
                  <button onClick={() => setFgFilter([])}
                    className={cn("px-2 py-1 rounded text-[10px] font-medium border transition-colors",
                      fgFilter.length === 0 ? 'bg-purple-500/20 border-purple-500/40 text-purple-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                    )}>Tous</button>
                  {[
                    { v: 'Extreme Fear', emoji: '😱', color: 'red' },
                    { v: 'Fear', emoji: '😰', color: 'orange' },
                    { v: 'Neutral', emoji: '😐', color: 'gray' },
                    { v: 'Greed', emoji: '😊', color: 'lime' },
                    { v: 'Extreme Greed', emoji: '🤑', color: 'green' },
                  ].map(({v, emoji, color}) => (
                    <button key={v} onClick={() => setFgFilter(prev => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v])}
                      className={cn("px-2 py-1 rounded text-[10px] font-medium border transition-colors",
                        fgFilter.includes(v)
                          ? color === 'red' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                            : color === 'orange' ? 'bg-orange-500/20 border-orange-500/40 text-orange-300'
                            : color === 'lime' ? 'bg-lime-500/20 border-lime-500/40 text-lime-300'
                            : color === 'green' ? 'bg-green-500/20 border-green-500/40 text-green-300'
                            : 'bg-gray-500/20 border-gray-500/40 text-gray-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{emoji} {v}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">BTC Trend 1H</label>
                <div className="flex gap-1">
                  {['ALL', 'BULLISH', 'BEARISH'].map(v => (
                    <button key={v} onClick={() => setBtcTrendFilter(v)}
                      className={cn("px-2 py-1 rounded text-[10px] font-medium border transition-colors",
                        btcTrendFilter === v
                          ? v === 'BULLISH' ? 'bg-green-500/20 border-green-500/40 text-green-300'
                            : v === 'BEARISH' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                            : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{v === 'ALL' ? '—' : v === 'BULLISH' ? '🟢 Bull' : '🔴 Bear'}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">ETH Trend 1H</label>
                <div className="flex gap-1">
                  {['ALL', 'BULLISH', 'BEARISH'].map(v => (
                    <button key={v} onClick={() => setEthTrendFilter(v)}
                      className={cn("px-2 py-1 rounded text-[10px] font-medium border transition-colors",
                        ethTrendFilter === v
                          ? v === 'BULLISH' ? 'bg-green-500/20 border-green-500/40 text-green-300'
                            : v === 'BEARISH' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                            : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{v === 'ALL' ? '—' : v === 'BULLISH' ? '🟢 Bull' : '🔴 Bear'}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">Alt Season</label>
                <div className="flex gap-1">
                  {['ALL', 'YES', 'NO'].map(v => (
                    <button key={v} onClick={() => setAltSeasonFilter(v)}
                      className={cn("px-2 py-1 rounded text-[10px] font-medium border transition-colors",
                        altSeasonFilter === v
                          ? v === 'YES' ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
                            : v === 'NO' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                            : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{v === 'ALL' ? '—' : v}</button>
                  ))}
                </div>
              </div>
            </div>
            {/* Row 3: PP, EC, TF, Conditions */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-4 gap-4">
              <div>
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">PP / EC</label>
                <div className="flex gap-2">
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] text-gray-500">PP:</span>
                    {['ALL', 'YES', 'NO'].map(v => (
                      <button key={v} onClick={() => setPpFilter(v)} className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium border transition-colors",
                        ppFilter === v ? v === 'YES' ? 'bg-green-500/20 border-green-500/40 text-green-300' : v === 'NO' ? 'bg-red-500/20 border-red-500/40 text-red-300' : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{v === 'ALL' ? '—' : v}</button>
                    ))}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] text-gray-500">EC:</span>
                    {['ALL', 'YES', 'NO'].map(v => (
                      <button key={v} onClick={() => setEcFilter(v)} className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium border transition-colors",
                        ecFilter === v ? v === 'YES' ? 'bg-green-500/20 border-green-500/40 text-green-300' : v === 'NO' ? 'bg-red-500/20 border-red-500/40 text-red-300' : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{v === 'ALL' ? '—' : v}</button>
                    ))}
                  </div>
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">Timeframe (multi-select)</label>
                <div className="flex gap-1 flex-wrap">
                  <button onClick={() => setTfFilter([])} className={cn("px-2 py-0.5 rounded text-[10px] font-medium border transition-colors",
                    tfFilter.length === 0 ? 'bg-purple-500/20 border-purple-500/40 text-purple-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                  )}>Tous</button>
                  {['15m', '30m', '1h', '4h', 'multi'].map(v => (
                    <button key={v} onClick={() => setTfFilter(prev => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v])}
                      className={cn("px-2 py-0.5 rounded text-[10px] font-medium border transition-colors",
                        tfFilter.includes(v) ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{v}</button>
                  ))}
                  {tfFilter.length > 0 && (
                    <button onClick={() => setTfFilter([])} className="px-2 py-0.5 rounded text-[10px] text-gray-400 border border-gray-700 hover:bg-gray-700">Clear</button>
                  )}
                </div>
              </div>
              <div className="col-span-2">
                <label className="text-[10px] text-gray-500 uppercase mb-1 block">Conditions (toutes requises)</label>
                <div className="flex gap-1 flex-wrap">
                  {['RSI', 'DMI', 'AST', 'CHoCH', 'Zone', 'Lazy', 'Vol', 'ST'].map(c => (
                    <button key={c} onClick={() => setCondFilters(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])}
                      className={cn("px-2 py-0.5 rounded text-[10px] font-medium border transition-colors",
                        condFilters.includes(c) ? 'bg-green-500/20 border-green-500/40 text-green-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:bg-gray-700'
                      )}>{c}</button>
                  ))}
                  {condFilters.length > 0 && (
                    <button onClick={() => setCondFilters([])} className="px-2 py-0.5 rounded text-[10px] text-gray-400 border border-gray-700 hover:bg-gray-700">Clear</button>
                  )}
                </div>
              </div>
            </div>
            {/* Dynamic Stats Bar */}
            {(() => {
              const res = filtered.filter(d => d.outcome === 'WIN' || d.outcome === 'LOSE')
              const wins = res.filter(d => d.outcome === 'WIN').length
              const losses = res.length - wins
              const wr = res.length > 0 ? (wins / res.length * 100) : 0
              const pnls = res.filter(d => d.pnl_pct != null).map(d => d.pnl_pct!)
              const avgPnl = pnls.length > 0 ? pnls.reduce((a, b) => a + b, 0) / pnls.length : 0
              const totalPnl = pnls.reduce((a, b) => a + b, 0)
              const ppCount = filtered.filter(d => (d.features_fingerprint || {}).pp).length
              const ecCount = filtered.filter(d => (d.features_fingerprint || {}).ec).length
              const avgScore = filtered.length > 0 ? filtered.reduce((s, d) => s + (d.scanner_score || 0), 0) / filtered.length : 0
              const big14 = filtered.filter(d => (d.pnl_pct || 0) >= 14).length
              return (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">Filtrees</div>
                    <div className="text-sm font-bold text-white">{filtered.length}<span className="text-xs text-gray-500">/{decisions.length}</span></div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">WR Resolu</div>
                    <div className={cn("text-sm font-bold", wr >= 50 ? "text-green-400" : wr >= 35 ? "text-yellow-400" : "text-red-400")}>{wr.toFixed(1)}%</div>
                    <div className="text-[10px] text-gray-600">{wins}W/{losses}L</div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">PnL Total</div>
                    <div className={cn("text-sm font-bold", totalPnl >= 0 ? "text-green-400" : "text-red-400")}>{totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(1)}%</div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">Avg PnL</div>
                    <div className={cn("text-sm font-bold", avgPnl >= 0 ? "text-green-400" : "text-red-400")}>{avgPnl >= 0 ? '+' : ''}{avgPnl.toFixed(2)}%</div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">Score Moy</div>
                    <div className="text-sm font-bold text-yellow-400">{avgScore.toFixed(1)}/10</div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">PP</div>
                    <div className="text-sm font-bold text-green-400">{ppCount}<span className="text-xs text-gray-600">/{filtered.length}</span></div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">EC</div>
                    <div className="text-sm font-bold text-green-400">{ecCount}<span className="text-xs text-gray-600">/{filtered.length}</span></div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                    <div className="text-[10px] text-gray-500">Big W +14%</div>
                    <div className="text-sm font-bold text-purple-400">{big14}</div>
                  </div>
                </div>
              )
            })()}
          </>)}

          {/* Quick Filters Bar — Date, Conf, PnL, Score, Accum, Grade */}
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-3 grid grid-cols-3 md:grid-cols-6 lg:grid-cols-12 gap-2">
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Date debut</label>
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Date fin</label>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Conf min</label>
              <input type="number" placeholder="0" value={minConf} onChange={e => setMinConf(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Conf max</label>
              <input type="number" placeholder="100" value={maxConf} onChange={e => setMaxConf(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">PnL min</label>
              <input type="number" placeholder="-100" value={minPnl} onChange={e => setMinPnl(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">PnL max</label>
              <input type="number" placeholder="100" value={maxPnl} onChange={e => setMaxPnl(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Score min</label>
              <input type="number" placeholder="0" min="0" max="10" value={minScore} onChange={e => setMinScore(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Accum min</label>
              <input type="number" placeholder="0" step="0.5" value={minAccum} onChange={e => setMinAccum(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 uppercase">Accum max</label>
              <input type="number" placeholder="30" step="0.5" value={maxAccum} onChange={e => setMaxAccum(e.target.value)}
                className="w-full px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
            </div>
            <div className="lg:col-span-3">
              <label className="text-[10px] text-gray-500 uppercase">Grade</label>
              <div className="flex gap-1 mt-0.5">
                <button onClick={() => setGradeFilter([])} className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium border", gradeFilter.length === 0 ? 'bg-purple-500/20 border-purple-500/40 text-purple-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>Tous</button>
                {['A+', 'A', '>=A', 'B', 'C'].map(g => (
                  <button key={g} onClick={() => setGradeFilter(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g])}
                    className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium border",
                      gradeFilter.includes(g)
                        ? g === 'A+' ? 'bg-green-500/20 border-green-500/40 text-green-300 font-bold' : g === 'A' || g === '>=A' ? 'bg-green-500/15 border-green-500/30 text-green-300' : g === 'B' ? 'bg-yellow-500/15 border-yellow-500/30 text-yellow-300' : 'bg-gray-600/20 border-gray-500/30 text-gray-300'
                        : 'bg-gray-800 border-gray-700 text-gray-500'
                    )}>{g}</button>
                ))}
              </div>
            </div>
          </div>

          {/* Results count + Quick Date + Presets */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-gray-400 font-medium">{filtered.length} resultats</span>
            <div className="flex items-center gap-1 pl-2 border-l border-gray-700">
              {[
                { label: "Auj", days: 0 },
                { label: "Hier", days: 1 },
                { label: "J-2", days: 2 },
                { label: "J-3", days: 3 },
                { label: "7j", days: 7 },
                { label: "Tout", days: -1 },
              ].map(({ label, days }) => {
                const gmt1Date = (daysAgo: number) => {
                  const now = new Date(); const gmt1Ms = now.getTime() + 3600000
                  return new Date(gmt1Ms - (daysAgo * 86400000)).toISOString().slice(0, 10)
                }
                const isActive = days === -1 ? !dateFrom && !dateTo : days === 7 ? dateFrom === gmt1Date(7) && !dateTo : dateFrom === gmt1Date(days) && dateTo === gmt1Date(days)
                return (
                  <button key={label} onClick={() => {
                    if (days === -1) { setDateFrom(''); setDateTo(''); return }
                    const t = gmt1Date(days)
                    if (days === 7) { setDateFrom(t); setDateTo(''); return }
                    setDateFrom(t); setDateTo(t)
                  }} className={cn("px-2 py-0.5 rounded text-[10px] font-medium border transition-colors", isActive ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300' : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700')}>{label}</button>
                )
              })}
              <div className="flex items-center gap-0.5">
                <span className="text-[10px] text-gray-500">J-</span>
                <input type="number" min="1" max="30" placeholder="X"
                  className="w-8 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-[10px] text-gray-200 text-center focus:outline-none focus:border-cyan-500"
                  onChange={e => { const v = parseInt(e.target.value); if (v > 0) { const now = new Date(); const t = new Date(now.getTime()+3600000-(v*86400000)).toISOString().slice(0,10); setDateFrom(t); setDateTo(t) }}} />
              </div>
            </div>
            <div className="flex items-center gap-1 pl-2 border-l border-gray-700">
              <span className="text-[10px] text-gray-600 mr-1">Presets:</span>
              <button onClick={() => {
                setDecisionFilter('ALL'); setMinBody4h('3'); setMinRange4h('3.5'); setDirFilter('green');
                setMaxDiPlus('45'); setMaxAdx('50'); setPpFilter('YES'); setEcFilter('YES');
                setMinChange24h('0'); setMaxChange24h('50'); setBtcTrendFilter('BULLISH'); setEthTrendFilter('BULLISH');
                setMinDiSpread(''); setMaxDiSpread(''); setMinAdx(''); setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20"
              >Gate V6</button>
              <button onClick={() => {
                setDecisionFilter('ALL'); setMinBody4h('3'); setMinRange4h('3.5'); setDirFilter('green');
                setMaxDiPlus('45'); setPpFilter('YES'); setEcFilter('YES');
                setMinChange24h('1'); setMaxChange24h('50'); setBtcTrendFilter('BULLISH'); setEthTrendFilter('BULLISH');
                setMinAdx('15'); setMaxAdx('35'); setMinDiSpread(''); setMaxDiSpread('');
                setMinVol1h(''); setMinVol4h(''); setMinVol24h(''); setMinVol48h('');
                setMaxBody4h(''); setMaxRange4h(''); setMinRsi(''); setMaxRsi('');
                setMinDiPlus(''); setMinDiMinus(''); setMaxDiMinus('');
                setMaxStc15m('0.99'); setMaxStc30m(''); setMaxStc1h(''); setMinTfBody('');
                setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20"
              >V8/V9 Ultra</button>
              <button onClick={() => {
                setDecisionFilter('ALL'); setMinBody4h('3'); setMinRange4h('3.5'); setDirFilter('green');
                setMaxDiPlus('65'); setPpFilter('YES'); setEcFilter('YES');
                setMinChange24h('1'); setMaxChange24h('50'); setBtcTrendFilter('BULLISH'); setEthTrendFilter('BULLISH');
                setMinAdx('15'); setMaxAdx('40'); setMinVol24h('200');
                setMinDiSpread(''); setMaxDiSpread('');
                setMinVol1h(''); setMinVol4h(''); setMinVol48h('');
                setMaxBody4h(''); setMaxRange4h(''); setMinRsi(''); setMaxRsi('');
                setMinDiPlus(''); setMinDiMinus(''); setMaxDiMinus('');
                setMaxStc15m('0.99'); setMaxStc30m(''); setMaxStc1h(''); setMinTfBody('');
                setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-orange-500/10 border-orange-500/30 text-orange-400 hover:bg-orange-500/20"
              >V8/V9+ Vol</button>
              <button onClick={() => {
                // Reset all advanced filters — let v8v9AllMode handle the logic
                setDecisionFilter('ALL'); setMinBody4h(''); setMinRange4h(''); setDirFilter('ALL');
                setMaxDiPlus(''); setPpFilter('ALL'); setEcFilter('ALL');
                setMinChange24h(''); setMaxChange24h(''); setBtcTrendFilter('ALL'); setEthTrendFilter('ALL');
                setMinAdx(''); setMaxAdx(''); setMinVol24h('');
                setMinDiSpread(''); setMaxDiSpread('');
                setMinVol1h(''); setMinVol4h(''); setMinVol48h('');
                setMaxBody4h(''); setMaxRange4h(''); setMinRsi(''); setMaxRsi('');
                setMinDiPlus(''); setMinDiMinus(''); setMaxDiMinus('');
                setV8v9AllMode(true); setShowAdvanced(false);
              }} className={cn("px-2 py-1 rounded text-[10px] font-medium border transition-colors",
                v8v9AllMode ? "bg-red-500/20 border-red-500/40 text-red-300" : "bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20"
              )}>V8/V9 All</button>
              <button onClick={() => {
                setMinAdx('15'); setMaxAdx('35'); setMinDiSpread(''); setMaxDiSpread('');
                setBtcTrendFilter('BULLISH'); setMinChange24h('1');
                setMinBody4h(''); setMinRange4h(''); setDirFilter('ALL');
                setPpFilter('ALL'); setEcFilter('ALL'); setEthTrendFilter('ALL');
                setMaxDiPlus(''); setMaxChange24h(''); setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-cyan-500/10 border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20"
              >Ultra Only</button>
              <button onClick={() => {
                setMinDiSpread('5'); setMaxDiSpread('15'); setMinAdx('25'); setMaxAdx('40');
                setMinBody4h(''); setMinRange4h(''); setDirFilter('ALL');
                setPpFilter('ALL'); setEcFilter('ALL'); setBtcTrendFilter('ALL'); setEthTrendFilter('ALL');
                setMinChange24h(''); setMaxChange24h(''); setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-purple-500/10 border-purple-500/30 text-purple-400 hover:bg-purple-500/20"
              >Sweet Spot</button>
              <button onClick={() => {
                setMinVol24h('100'); setMinBody4h('3');
                setMinAdx(''); setMaxAdx(''); setMinDiSpread(''); setMaxDiSpread('');
                setDirFilter('ALL'); setPpFilter('ALL'); setEcFilter('ALL');
                setBtcTrendFilter('ALL'); setEthTrendFilter('ALL');
                setMinChange24h(''); setMaxChange24h(''); setMinRange4h(''); setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
              >Body+Vol</button>
            </div>
          </div>

          {/* Column Picker */}
          <div className="relative inline-block">
            <button onClick={() => setShowColPicker(!showColPicker)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs text-gray-300 border border-gray-700 transition-colors">
              <Eye className="w-3.5 h-3.5" /> Colonnes ({visibleCols.size}/{ALL_COLUMNS.length})
            </button>
            {showColPicker && (
              <div className="absolute top-full left-0 mt-1 z-50 bg-gray-900 border border-gray-700 rounded-lg p-2 shadow-xl grid grid-cols-5 gap-1 min-w-[500px]">
                {ALL_COLUMNS.map(c => (
                  <label key={c.key} className={cn("flex items-center gap-1.5 px-2 py-1 rounded text-[10px] cursor-pointer transition-colors",
                    visibleCols.has(c.key) ? "bg-purple-500/15 text-purple-300" : "text-gray-500 hover:text-gray-300"
                  )}>
                    <input type="checkbox" checked={visibleCols.has(c.key)} onChange={() => toggleCol(c.key)}
                      className="w-3 h-3 rounded border-gray-600 bg-gray-800 text-purple-500 focus:ring-0 focus:ring-offset-0" />
                    {c.label}
                  </label>
                ))}
                <div className="col-span-5 flex gap-2 mt-1 pt-1 border-t border-gray-800">
                  <button onClick={() => setVisibleCols(new Set(ALL_COLUMNS.map(c => c.key)))}
                    className="text-[10px] text-gray-400 hover:text-gray-200">Tout</button>
                  <button onClick={() => setVisibleCols(new Set(ALL_COLUMNS.filter(c => c.default).map(c => c.key)))}
                    className="text-[10px] text-gray-400 hover:text-gray-200">Reset</button>
                  <button onClick={() => setVisibleCols(new Set(['date','pair','pnl','pnl_max']))}
                    className="text-[10px] text-gray-400 hover:text-gray-200">Minimal</button>
                </div>
              </div>
            )}
          </div>

          {/* Table */}
          <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
            <div className="overflow-x-auto overflow-y-auto max-h-[70vh]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-30 bg-gray-900">
                  <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase">
                    {col('date') && <th className="px-2 py-2 text-left cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('timestamp')}>Date{sortIcon('timestamp')}</th>}
                    {col('pair') && <th className="px-2 py-2 text-left cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('pair')}>Paire{sortIcon('pair')}</th>}
                    {col('vip') && <th className="px-1 py-2 text-center cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('vip')}>VIP{sortIcon('vip')}</th>}
                    {col('tfs') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('tfs')}>TFs{sortIcon('tfs')}</th>}
                    {col('score') && <th className="px-1 py-2 text-center cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('score')}>Score{sortIcon('score')}</th>}
                    {col('di_plus') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('di_plus')}>DI+{sortIcon('di_plus')}</th>}
                    {col('di_minus') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('di_minus')}>DI-{sortIcon('di_minus')}</th>}
                    {col('adx') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('adx')}>ADX{sortIcon('adx')}</th>}
                    {col('di_spread') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('di_spread')}>D±{sortIcon('di_spread')}</th>}
                    {col('rsi') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('rsi')}>RSI{sortIcon('rsi')}</th>}
                    {col('change24h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('change24h')}>24h%{sortIcon('change24h')}</th>}
                    {col('body4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('body4h')}>Body{sortIcon('body4h')}</th>}
                    {col('range4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('range4h')}>Range{sortIcon('range4h')}</th>}
                    {col('vol_1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('vol_1h')}>V1h{sortIcon('vol_1h')}</th>}
                    {col('vol_4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('vol_4h')}>V4h{sortIcon('vol_4h')}</th>}
                    {col('vol_24h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('vol_24h')}>V24h{sortIcon('vol_24h')}</th>}
                    {col('vol_48h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('vol_48h')}>V48h{sortIcon('vol_48h')}</th>}
                    {col('stc_15m') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('stc_15m')}>S15{sortIcon('stc_15m')}</th>}
                    {col('stc_30m') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('stc_30m')}>S30{sortIcon('stc_30m')}</th>}
                    {col('stc_1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('stc_1h')}>S1h{sortIcon('stc_1h')}</th>}
                    {col('tf_body') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('tf_body')}>TFB{sortIcon('tf_body')}</th>}
                    {col('fg') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('fg')}>F&G{sortIcon('fg')}</th>}
                    {col('btc') && <th className="px-1 py-2 text-center text-[10px]">BTC</th>}
                    {col('eth') && <th className="px-1 py-2 text-center text-[10px]">ETH</th>}
                    {col('pp') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('pp')}>PP{sortIcon('pp')}</th>}
                    {col('ec') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('ec')}>EC{sortIcon('ec')}</th>}
                    {col('accum') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('accum')}>Accum{sortIcon('accum')}</th>}
                    {col('decision') && <th className="px-1 py-2 text-center cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('decision')}>Decision{sortIcon('decision')}</th>}
                    {col('grade') && <th className="px-1 py-2 text-center cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('grade')}>Grade{sortIcon('grade')}</th>}
                    {col('confidence') && <th className="px-1 py-2 text-center cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('confidence')}>Conf{sortIcon('confidence')}</th>}
                    {col('outcome') && <th className="px-1 py-2 text-center cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('outcome')}>Outcome{sortIcon('outcome')}</th>}
                    {col('pnl') && <th className="px-1 py-2 text-right cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('pnl')}>PnL{sortIcon('pnl')}</th>}
                    {col('pnl_max') && <th className="px-1 py-2 text-right cursor-pointer hover:text-gray-200 text-[10px]" onClick={() => toggleSort('pnl_max')}>Max{sortIcon('pnl_max')}</th>}
                    {col('tv') && <th className="px-1 py-2 text-center text-[10px]">TV</th>}
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
                        {(() => {
                          const fp = d.features_fingerprint || {}
                          const diPlus = fp.di_plus_4h; const diMinus = fp.di_minus_4h; const adx = fp.adx_4h; const rsi = fp.rsi
                          const tfs = fp.timeframes || []
                          const days = fp.accumulation_days
                          const volSpikes = [fp.vol_spike_vs_1h, fp.vol_spike_vs_4h, fp.vol_spike_vs_24h, fp.vol_spike_vs_48h]
                          const volKeys = ['vol_1h','vol_4h','vol_24h','vol_48h']
                          const volLabels = ['1h','4h','24h','48h']
                          const dash = <span className="text-gray-700 text-[10px]">—</span>
                          return (<>
                            {col('date') && <td className="px-2 py-1 text-[10px] whitespace-nowrap">
                              {(() => {
                                const alertTs = (d as any).alert_data?.alert_timestamp
                                const processTs = d.timestamp
                                if (alertTs && processTs) {
                                  const gap = Math.round((new Date(processTs).getTime() - new Date(alertTs).getTime()) / 60000)
                                  return <div>
                                    <div className="text-cyan-400" title="Heure détection scanner">{toGMT1(alertTs)}</div>
                                    {gap > 5 && <div className="text-gray-600" title={`Traité ${gap}min après`}>+{gap}m</div>}
                                  </div>
                                }
                                return <div className="text-gray-400">{processTs ? toGMT1(processTs) : '—'}</div>
                              })()}
                            </td>}
                            {col('pair') && <td className="px-2 py-1 font-medium text-gray-200 text-xs"><a href={`https://www.tradingview.com/chart/?symbol=BINANCE%3A${d.pair}`} target="_blank" rel="noopener noreferrer" className="hover:text-purple-400" onClick={e => e.stopPropagation()}>{d.pair?.replace('USDT','')}<span className="text-gray-600 font-normal">USDT</span></a></td>}
                            {col('vip') && <td className="px-1 py-1 text-center">{fp.is_high_ticket ? <span title={`HT ${fp.vip_score}/5`} className="cursor-help">🏆</span> : fp.is_vip ? <span title={`VIP ${fp.vip_score}/5`} className="cursor-help">⭐</span> : dash}</td>}
                            {col('tfs') && <td className="px-1 py-1 text-center"><span className="text-[10px] text-gray-400">{tfs.length > 0 ? tfs.join(',') : '—'}</span></td>}
                            {col('score') && <td className="px-1 py-1 text-center">{d.scanner_score ? <span className={cn("text-xs font-bold", d.scanner_score >= 8 ? 'text-green-400' : d.scanner_score >= 6 ? 'text-yellow-400' : 'text-red-400')}>{d.scanner_score}</span> : dash}</td>}
                            {col('di_plus') && <td className="px-1 py-1 text-center">{diPlus ? <span className={cn("text-[10px] font-mono", diPlus >= 30 ? 'text-green-400' : 'text-gray-400')}>{diPlus.toFixed(0)}</span> : dash}</td>}
                            {col('di_minus') && <td className="px-1 py-1 text-center">{diMinus ? <span className={cn("text-[10px] font-mono", diMinus <= 15 ? 'text-green-400' : diMinus >= 25 ? 'text-red-400' : 'text-gray-400')}>{diMinus.toFixed(0)}</span> : dash}</td>}
                            {col('adx') && <td className="px-1 py-1 text-center">{adx ? <span className={cn("text-[10px] font-mono", adx >= 40 ? 'text-green-400' : adx >= 25 ? 'text-yellow-400' : 'text-gray-400')}>{adx.toFixed(0)}</span> : dash}</td>}
                            {col('di_spread') && <td className="px-1 py-1 text-center">{diPlus != null && diMinus != null ? (() => { const sp = diPlus - diMinus; const c2 = sp >= 40 ? 'text-red-400 font-bold' : sp >= 5 && sp <= 15 ? 'text-green-400' : sp < 0 ? 'text-red-400' : 'text-gray-400'; return <span className={cn("text-[10px] font-mono", c2)} title={`DI+ ${diPlus.toFixed(0)} - DI- ${diMinus.toFixed(0)}`}>{sp >= 0 ? '+' : ''}{sp.toFixed(0)}</span> })() : dash}</td>}
                            {col('rsi') && <td className="px-1 py-1 text-center">{rsi ? <span className={cn("text-[10px] font-mono", rsi >= 70 ? 'text-red-400' : rsi <= 30 ? 'text-green-400' : 'text-gray-400')}>{rsi.toFixed(0)}</span> : dash}</td>}
                            {col('change24h') && <td className="px-1 py-1 text-center">{fp.change_24h_pct != null ? <span className={cn("text-[10px] font-mono", fp.change_24h_pct >= 5 ? 'text-green-400' : fp.change_24h_pct <= -5 ? 'text-red-400' : 'text-gray-400')}>{fp.change_24h_pct >= 0 ? '+' : ''}{fp.change_24h_pct.toFixed(1)}%</span> : dash}</td>}
                            {col('body4h') && <td className="px-1 py-1 text-center">{fp.candle_4h_body_pct != null ? <span className={cn("text-[10px] font-mono", fp.candle_4h_direction === 'green' ? 'text-green-400' : 'text-red-400')}>{fp.candle_4h_body_pct.toFixed(1)}%</span> : dash}</td>}
                            {col('range4h') && <td className="px-1 py-1 text-center">{fp.candle_4h_range_pct != null ? <span className={cn("text-[10px] font-mono", fp.candle_4h_range_pct >= 5 ? 'text-yellow-400' : 'text-gray-400')}>{fp.candle_4h_range_pct.toFixed(1)}%</span> : dash}</td>}
                            {volSpikes.map((spike, i) => col(volKeys[i]) && <td key={volKeys[i]} className="px-1 py-1 text-center">{spike != null ? <span className={cn("text-[10px] font-mono", spike >= 200 ? 'text-green-400 font-bold' : spike >= 50 ? 'text-green-400' : spike >= 0 ? 'text-gray-400' : 'text-red-400')} title={`Vol ${volLabels[i]}: ${spike >= 0 ? '+' : ''}${spike}%`}>{spike >= 0 ? '+' : ''}{spike > 999 ? `${(spike/1000).toFixed(1)}k` : spike.toFixed(0)}%</span> : dash}</td>)}
                            {[['stc_15m',fp.stc_15m],['stc_30m',fp.stc_30m],['stc_1h',fp.stc_1h]].map(([k,v]) => col(k as string) && <td key={k as string} className="px-1 py-1 text-center">{v != null ? <span className={cn("text-[10px] font-mono", (v as number) < 0.05 ? 'text-green-400 font-bold' : (v as number) < 0.2 ? 'text-green-400' : (v as number) < 0.5 ? 'text-yellow-400' : 'text-gray-400')} title={`STC ${(k as string).replace('stc_','')}: ${(v as number).toFixed(3)}`}>{(v as number).toFixed(2)}</span> : dash}</td>)}
                            {col('tf_body') && (() => {
                              const alertTfs = tfs || []
                              const tfBodies = alertTfs.map((tf: string) => ({ tf, body: fp[`candle_${tf}_body_pct`] as number | undefined, dir: fp[`candle_${tf}_direction`] as string | undefined })).filter((x: any) => x.body != null)
                              if (tfBodies.length === 0) return <td className="px-1 py-1 text-center">{dash}</td>
                              const best = tfBodies.reduce((a: any, b: any) => (b.body > a.body ? b : a), tfBodies[0])
                              return <td className="px-1 py-1 text-center">
                                <span className={cn("text-[10px] font-mono", best.body >= 10 ? 'text-green-400 font-bold' : best.body >= 5 ? 'text-green-400' : best.body >= 3 ? 'text-yellow-400' : 'text-gray-400')}
                                  title={tfBodies.map((x: any) => `${x.tf}: ${x.body.toFixed(1)}% ${x.dir}`).join(' | ')}>
                                  {best.body.toFixed(1)}%<span className="text-[8px] text-gray-600 ml-0.5">{best.tf}</span>
                                </span>
                              </td>
                            })()}
                            {col('fg') && <td className="px-1 py-1 text-center">{fp.fear_greed_value != null ? (() => { const v = fp.fear_greed_value; const c3 = v <= 25 ? 'text-red-400' : v <= 45 ? 'text-orange-400' : v <= 55 ? 'text-gray-400' : v <= 75 ? 'text-lime-400' : 'text-green-400'; const em = v <= 25 ? '😱' : v <= 45 ? '😰' : v <= 55 ? '😐' : v <= 75 ? '😊' : '🤑'; return <span className={cn("text-[10px] font-mono cursor-help", c3)} title={fp.fear_greed_label}>{em}{v}</span> })() : dash}</td>}
                            {col('btc') && <td className="px-1 py-1 text-center">{fp.btc_trend_1h ? <span className={cn("text-[10px]", fp.btc_trend_1h === 'BULLISH' ? 'text-green-400' : 'text-red-400')}>{fp.btc_trend_1h === 'BULLISH' ? '🟢' : '🔴'}</span> : dash}</td>}
                            {col('eth') && <td className="px-1 py-1 text-center">{fp.eth_trend_1h ? <span className={cn("text-[10px]", fp.eth_trend_1h === 'BULLISH' ? 'text-green-400' : 'text-red-400')}>{fp.eth_trend_1h === 'BULLISH' ? '🟢' : '🔴'}</span> : dash}</td>}
                            {col('pp') && <td className="px-1 py-1 text-center">{fp.pp ? <span className="text-green-400 text-[10px]">✓</span> : <span className="text-gray-700 text-[10px]">✗</span>}</td>}
                            {col('ec') && <td className="px-1 py-1 text-center">{fp.ec ? <span className="text-green-400 text-[10px]">✓</span> : <span className="text-gray-700 text-[10px]">✗</span>}</td>}
                            {col('accum') && <td className="px-1 py-1 text-center">{days && days > 0 ? <span className={cn("text-[10px]", days >= 5 ? 'text-green-400' : days >= 3 ? 'text-yellow-400' : 'text-gray-400')}>{days.toFixed(1)}j</span> : dash}</td>}
                            {col('decision') && <td className="px-1 py-1 text-center"><span className={cn("px-1.5 py-0.5 rounded-full text-[10px] font-medium border", decStyle.bg, decStyle.color)}>{decStyle.icon} {decStyle.label}</span></td>}
                            {col('grade') && <td className="px-1 py-1 text-center">{(() => { const gr = fp.quality_grade; if (!gr) return dash; const gc = gr === 'A+' ? 'text-green-400 font-bold' : gr === 'A' ? 'text-green-400' : gr === 'B' ? 'text-yellow-400' : 'text-gray-500'; return <span className={`${gc} text-xs cursor-help`} title={(fp.quality_details || []).join(', ') || `${fp.quality_axes||0}/4`}>{gr}</span> })()}</td>}
                            {col('confidence') && <td className="px-1 py-1 text-center"><span className={cn("text-[10px] font-mono", d.agent_confidence >= 0.7 ? 'text-green-400' : d.agent_confidence >= 0.5 ? 'text-yellow-400' : 'text-gray-400')}>{((d.agent_confidence || 0) * 100).toFixed(0)}%</span></td>}
                            {col('outcome') && <td className="px-1 py-1 text-center"><span className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium", outStyle.bg, outStyle.color)}>{outStyle.label}</span></td>}
                            {col('pnl') && (() => {
                              const resolved = d.outcome && d.outcome !== 'PENDING'
                              const pnlVal = resolved && d.pnl_at_close != null ? d.pnl_at_close : (d.pnl_pct ?? null)
                              return <td className="px-1 py-1 text-right">{pnlVal != null ? (<div><span className={cn("font-mono text-[10px]", pnlVal >= 0 ? 'text-green-400' : 'text-red-400')}>{pnlVal >= 0 ? '+' : ''}{pnlVal.toFixed(1)}%</span>{d.outcome_at && d.timestamp ? (() => { const h = (new Date(d.outcome_at).getTime() - new Date(d.timestamp).getTime()) / 3600000; const dj = Math.floor(h/24); const dh = Math.floor(h%24); return <div className="text-[8px] text-gray-500">{dj > 0 ? `${dj}j${dh}h` : `${dh}h`}</div> })() : null}</div>) : dash}</td>
                            })()}
                            {col('pnl_max') && <td className="px-1 py-1 text-right">{d.pnl_max != null ? (<div><span className={cn("font-mono text-[10px]", (d.pnl_max||0) >= 0 ? 'text-green-400/70' : 'text-red-400/70')}>{(d.pnl_max||0) >= 0 ? '+' : ''}{(d.pnl_max||0).toFixed(1)}%</span>{d.pnl_max_at && d.timestamp ? (() => { const h = (new Date(d.pnl_max_at).getTime() - new Date(d.timestamp).getTime()) / 3600000; const dj = Math.floor(h/24); const dh = Math.floor(h%24); return <div className="text-[8px] text-gray-500">{dj > 0 ? `${dj}j${dh}h` : `${dh}h`}</div> })() : null}</div>) : dash}</td>}
                            {col('tv') && <td className="px-1 py-1 text-center"><a href={`https://www.tradingview.com/chart/?symbol=BINANCE%3A${d.pair}`} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 text-[10px]" onClick={e => e.stopPropagation()}>📊</a></td>}
                          </>)
                        })()}
                      </tr>
                    )
                  })}
                  {paged.length === 0 && (
                    <tr>
                      <td colSpan={24} className="px-4 py-12 text-center text-gray-500">
                        Aucune decision trouvee
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">
                  Page {currentPage}/{totalPages} — {filtered.length} resultats
                </span>
                <div className="flex items-center gap-1">
                  {PAGE_SIZE_OPTIONS.map(n => (
                    <button key={n} onClick={() => { setPerPage(n); setCurrentPage(1) }}
                      className={cn("px-2 py-0.5 rounded text-[10px] font-medium border transition-colors",
                        perPage === n ? "bg-purple-500/20 border-purple-500/40 text-purple-300" : "bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300"
                      )}>{n}</button>
                  ))}
                </div>
              </div>
              {totalPages > 1 && (
                <div className="flex items-center gap-1">
                  <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronsLeft className="w-4 h-4 text-gray-400" /></button>
                  <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronLeft className="w-4 h-4 text-gray-400" /></button>
                  <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronRight className="w-4 h-4 text-gray-400" /></button>
                  <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages} className="p-1.5 rounded hover:bg-gray-800 disabled:opacity-30"><ChevronsRight className="w-4 h-4 text-gray-400" /></button>
                </div>
              )}
            </div>
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
