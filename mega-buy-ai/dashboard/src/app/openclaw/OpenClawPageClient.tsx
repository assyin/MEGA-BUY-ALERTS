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
    { key: 'adx_minus_dim', label: 'A−D−', default: true },
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
    // ─── Tier 3 — analyse OpenClaw (default off, opt-in via column picker) ───
    { key: 'prog', label: 'Prog', default: false },
    { key: 'bonus_n', label: 'Bonus', default: false },
    { key: 'fib4h', label: 'Fib4H', default: false },
    { key: 'fib1h', label: 'Fib1H', default: false },
    { key: 'vp4h', label: 'VP4H', default: false },
    { key: 'vp1h', label: 'VP1H', default: false },
    { key: 'ob4h', label: 'OB4H', default: false },
    { key: 'ob1h', label: 'OB1H', default: false },
    { key: 'macd4h', label: 'MACD4', default: false },
    { key: 'macd1h', label: 'MACD1', default: false },
    { key: 'stoch4h', label: 'Stoch4', default: false },
    { key: 'stoch1h', label: 'Stoch1', default: false },
    { key: 'ema_st4h', label: 'EMS4', default: false },
    { key: 'ema_st1h', label: 'EMS1', default: false },
    { key: 'bb4h', label: 'BB4', default: false },
    { key: 'fvg4h', label: 'FVG4', default: false },
    { key: 'adx1h', label: 'ADX1', default: false },
    { key: 'rsi_mtf', label: 'RsiMtf', default: false },
    { key: 'ml', label: 'ML', default: false },
  ] as const
  const [visibleCols, setVisibleCols] = useState<Set<string>>(() => new Set(ALL_COLUMNS.filter(c => c.default).map(c => c.key)))
  const [showColPicker, setShowColPicker] = useState(false)
  // View presets — quick switch between predefined column sets
  const VIEW_CLASSIC = ALL_COLUMNS.filter(c => c.default).map(c => c.key)
  const VIEW_OPENCLAW = ['date', 'pair', 'vip', 'score', 'decision', 'confidence', 'outcome', 'pnl', 'pnl_max',
                         'prog', 'bonus_n', 'fib4h', 'vp4h', 'ob4h', 'macd4h', 'stoch4h', 'ema_st4h',
                         'bb4h', 'fvg4h', 'adx1h', 'rsi_mtf', 'ml']
  const setsEqual = (a: Set<string>, b: string[]) => a.size === b.length && b.every(k => a.has(k))
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
  const [v4GateFilter, setV4GateFilter] = useState<string>('ALL') // ALL, PASS, REJECT
  // V4 gate config (editable — defaults match actual V4 strategy)
  const [v4MinScore, setV4MinScore] = useState<number>(8)
  const [v4AllowVip, setV4AllowVip] = useState<boolean>(true)
  const [v4AllowHt, setV4AllowHt] = useState<boolean>(true)
  const [v4AllowNoVip, setV4AllowNoVip] = useState<boolean>(false)
  const [v4CandleDir, setV4CandleDir] = useState<'green' | 'red' | 'any'>('green')

  // ─── Tier 1 — features_fingerprint based ───
  // Body % per TF
  const [minBody15m, setMinBody15m] = useState(''); const [maxBody15m, setMaxBody15m] = useState('')
  const [minBody30m, setMinBody30m] = useState(''); const [maxBody30m, setMaxBody30m] = useState('')
  const [minBody1h, setMinBody1h] = useState(''); const [maxBody1h, setMaxBody1h] = useState('')
  // Range % per TF
  const [minRange15m, setMinRange15m] = useState(''); const [maxRange15m, setMaxRange15m] = useState('')
  const [minRange30m, setMinRange30m] = useState(''); const [maxRange30m, setMaxRange30m] = useState('')
  const [minRange1h, setMinRange1h] = useState(''); const [maxRange1h, setMaxRange1h] = useState('')
  // Direction per TF (15m, 30m, 1h)
  const [dir15m, setDir15m] = useState<'ALL' | 'green' | 'red'>('ALL')
  const [dir30m, setDir30m] = useState<'ALL' | 'green' | 'red'>('ALL')
  const [dir1h, setDir1h] = useState<'ALL' | 'green' | 'red'>('ALL')
  // BTC dominance / ETH dominance / Others.D
  const [minBtcDom, setMinBtcDom] = useState(''); const [maxBtcDom, setMaxBtcDom] = useState('')
  const [minEthDom, setMinEthDom] = useState(''); const [maxEthDom, setMaxEthDom] = useState('')
  const [minOthersD, setMinOthersD] = useState(''); const [maxOthersD, setMaxOthersD] = useState('')
  // BTC / ETH 24h change
  const [minBtc24h, setMinBtc24h] = useState(''); const [maxBtc24h, setMaxBtc24h] = useState('')
  const [minEth24h, setMinEth24h] = useState(''); const [maxEth24h, setMaxEth24h] = useState('')
  // Volume USDT min
  const [minVolUsdt, setMinVolUsdt] = useState('')
  // Accumulation hours
  const [minAccumH, setMinAccumH] = useState(''); const [maxAccumH, setMaxAccumH] = useState('')
  // Quality axes count
  const [minQualityAxes, setMinQualityAxes] = useState('')
  // BTC season / ETH season toggles
  const [btcSeasonFilter, setBtcSeasonFilter] = useState<'ALL' | 'YES' | 'NO'>('ALL')
  const [ethSeasonFilter, setEthSeasonFilter] = useState<'ALL' | 'YES' | 'NO'>('ALL')

  // ─── Tier 2 — alerts table based ───
  // LazyBar 4H color
  const [lazy4hFilter, setLazy4hFilter] = useState<string[]>([]) // empty=ALL, can contain 'Red','Yellow','Green','Navy'
  // DMI cross 4H
  const [dmiCross4hFilter, setDmiCross4hFilter] = useState<'ALL' | 'YES' | 'NO'>('ALL')
  // Bougie 4H validation
  const [bougie4hFilter, setBougie4hFilter] = useState<'ALL' | 'YES' | 'NO'>('ALL')
  // Emotion
  const [emotionFilter, setEmotionFilter] = useState<string[]>([]) // empty=ALL, can contain 'STRONG','NEUTRAL','WEAK'
  // RSI moves min per TF (15m/30m/1h/4h)
  const [minRsiMv15m, setMinRsiMv15m] = useState(''); const [minRsiMv1h, setMinRsiMv1h] = useState(''); const [minRsiMv4h, setMinRsiMv4h] = useState('')
  // DI+ moves min per TF
  const [minDiPMv15m, setMinDiPMv15m] = useState(''); const [minDiPMv1h, setMinDiPMv1h] = useState(''); const [minDiPMv4h, setMinDiPMv4h] = useState('')
  // EC moves min per TF
  const [minEcMv15m, setMinEcMv15m] = useState(''); const [minEcMv1h, setMinEcMv1h] = useState(''); const [minEcMv4h, setMinEcMv4h] = useState('')
  // Max profit potentiel
  const [minMaxProfit, setMinMaxProfit] = useState(''); const [maxMaxProfit, setMaxMaxProfit] = useState('')
  // LazyBar color per TF (15m, 30m, 1h)
  const [lazy15mFilter, setLazy15mFilter] = useState<string[]>([])
  const [lazy30mFilter, setLazy30mFilter] = useState<string[]>([])
  const [lazy1hFilter, setLazy1hFilter] = useState<string[]>([])

  // ─── Tier 3 — analyze_alert structured indicators ───
  const [minProgCount, setMinProgCount] = useState('')         // 0-5 effective
  const [minBonusCount, setMinBonusCount] = useState('')       // 0-23
  const [fib4hF, setFib4hF] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [fib1hF, setFib1hF] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [vpPos1h, setVpPos1h] = useState<string[]>([])         // IN_VA, ABOVE_VAH, BELOW_VAL
  const [vpPos4h, setVpPos4h] = useState<string[]>([])
  const [obPos1h, setObPos1h] = useState<string[]>([])         // ABOVE, INSIDE, BELOW
  const [obPos4h, setObPos4h] = useState<string[]>([])
  const [obStrength1h, setObStrength1h] = useState<string[]>([]) // STRONG, MEDIUM, WEAK
  const [obStrength4h, setObStrength4h] = useState<string[]>([])
  const [obMitig1h, setObMitig1h] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [obMitig4h, setObMitig4h] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [fvgPos1h, setFvgPos1h] = useState<string[]>([])
  const [fvgPos4h, setFvgPos4h] = useState<string[]>([])
  const [macd1hTrend, setMacd1hTrend] = useState<string[]>([]) // BULLISH, BEARISH
  const [macd4hTrend, setMacd4hTrend] = useState<string[]>([])
  const [macd1hGrow, setMacd1hGrow] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [macd4hGrow, setMacd4hGrow] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [bb1hSqueeze, setBb1hSqueeze] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [bb4hSqueeze, setBb4hSqueeze] = useState<'ALL'|'YES'|'NO'>('ALL')
  const [stoch1hZone, setStoch1hZone] = useState<string[]>([]) // OVERSOLD, NEUTRAL, OVERBOUGHT
  const [stoch4hZone, setStoch4hZone] = useState<string[]>([])
  const [minEmaStack1h, setMinEmaStack1h] = useState('')        // 0-4
  const [minEmaStack4h, setMinEmaStack4h] = useState('')
  const [minAdx1h, setMinAdx1h] = useState(''); const [maxAdx1h, setMaxAdx1h] = useState('')
  const [minRsiMtf, setMinRsiMtf] = useState('')                // 0-3
  const [minMlScore, setMinMlScore] = useState('')              // 0-1
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
  const [maxVol1h, setMaxVol1h] = useState('')
  const [maxVol4h, setMaxVol4h] = useState('')
  const [maxVol24h, setMaxVol24h] = useState('')
  const [maxVol48h, setMaxVol48h] = useState('')
  const [excludeAllRedVol, setExcludeAllRedVol] = useState(false)
  const [excludeGrayIndicators, setExcludeGrayIndicators] = useState(false)
  // DI Spread filter
  const [minDiSpread, setMinDiSpread] = useState('')
  const [maxDiSpread, setMaxDiSpread] = useState('')
  // ADX - DI- filter
  const [minAdxDim, setMinAdxDim] = useState('')
  const [maxAdxDim, setMaxAdxDim] = useState('')
  // STC filters
  const [maxStc15m, setMaxStc15m] = useState('')
  const [maxStc30m, setMaxStc30m] = useState('')
  const [maxStc1h, setMaxStc1h] = useState('')
  const [minStc15m, setMinStc15m] = useState('')
  const [minStc30m, setMinStc30m] = useState('')
  const [minStc1h, setMinStc1h] = useState('')
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
      // Load agent_memory — last 14 days by default (use date picker for older)
      const since30d = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10)
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
          // Batch load in parallel chunks (was sequential — 37x slower)
          const CHUNK = 300
          const chunks: string[][] = []
          for (let i = 0; i < alertIds.length; i += CHUNK) {
            chunks.push(alertIds.slice(i, i + CHUNK))
          }
          const results = await Promise.all(chunks.map(chunk =>
            supabase
              .from("alerts")
              .select("id,alert_timestamp,rsi_check,dmi_check,ast_check,choch,zone,lazy,vol,st,puissance,vol_pct,lazy_values,lazy_moves,ec_moves,emotion,rsi_moves,di_plus_moves,di_minus_moves,adx_moves,nb_timeframes,lazy_4h,bougie_4h,dmi_cross_4h,max_profit_pct,max_profit_hours,body_4h,range_4h")
              .in("id", chunk)
          ))
          for (const { data: alertData } of results) {
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

      // Load usage/timing in background — don't block the main table render
      // (these endpoints can take minutes when the openclaw backend is busy)
      const timeoutFetch = async (url: string, ms: number) => {
        try {
          const res = await Promise.race([
            fetch(url).then(r => r.ok ? r.json() : null).catch(() => null),
            new Promise<null>(resolve => setTimeout(() => resolve(null), ms)),
          ])
          return res
        } catch {
          return null
        }
      }
      timeoutFetch('/api/openclaw/usage', 8000).then(u => { if (u) setUsage(u) }).catch(() => {})
      timeoutFetch('/api/openclaw/timing', 8000).then(t => { if (t) setTiming(t) }).catch(() => {})
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
      // V4 Gate filter — fully configurable from the UI
      if (v4GateFilter !== 'ALL') {
        const fpv4 = d.features_fingerprint || {}
        const score = d.scanner_score || 0
        const isVip = fpv4.is_vip === true
        const isHt = fpv4.is_high_ticket === true
        const isNoVip = !isVip && !isHt
        // 1) score gate
        let passes = score >= v4MinScore
        // 2) VIP gate — at least one allowed bucket must match
        if (passes) {
          passes = (v4AllowVip && isVip) || (v4AllowHt && isHt) || (v4AllowNoVip && isNoVip)
        }
        // 3) candle direction gate
        if (passes && v4CandleDir !== 'any') {
          passes = fpv4.candle_4h_direction === v4CandleDir
        }
        if (v4GateFilter === 'PASS' && !passes) return false
        if (v4GateFilter === 'REJECT' && passes) return false
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
      if (maxVol1h && (fp2.vol_spike_vs_1h == null || fp2.vol_spike_vs_1h > parseFloat(maxVol1h))) return false
      if (maxVol4h && (fp2.vol_spike_vs_4h == null || fp2.vol_spike_vs_4h > parseFloat(maxVol4h))) return false
      if (maxVol24h && (fp2.vol_spike_vs_24h == null || fp2.vol_spike_vs_24h > parseFloat(maxVol24h))) return false
      if (maxVol48h && (fp2.vol_spike_vs_48h == null || fp2.vol_spike_vs_48h > parseFloat(maxVol48h))) return false
      if (excludeAllRedVol) {
        const v1 = fp2.vol_spike_vs_1h, v4 = fp2.vol_spike_vs_4h, v24 = fp2.vol_spike_vs_24h, v48 = fp2.vol_spike_vs_48h
        if (v1 != null && v4 != null && v24 != null && v48 != null && v1 < 0 && v4 < 0 && v24 < 0 && v48 < 0) return false
      }
      if (excludeGrayIndicators) {
        const diP = fp2.di_plus_4h, diM = fp2.di_minus_4h, adxV = fp2.adx_4h, rsiV = fp2.rsi
        const sp = (diP != null && diM != null) ? diP - diM : null
        let grayCount = 0
        if (diP != null && diP < 30) grayCount++
        if (diM != null && diM > 15 && diM < 25) grayCount++
        if (adxV != null && adxV < 25) grayCount++
        if (sp != null && !(sp >= 5 && sp <= 15) && !(sp >= 40) && !(sp < 0)) grayCount++
        if (rsiV != null && rsiV > 30 && rsiV < 70) grayCount++
        if (grayCount >= 4) return false
      }
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
      if (minStc15m && (fp2.stc_15m == null || fp2.stc_15m < parseFloat(minStc15m))) return false
      if (minStc30m && (fp2.stc_30m == null || fp2.stc_30m < parseFloat(minStc30m))) return false
      if (minStc1h && (fp2.stc_1h == null || fp2.stc_1h < parseFloat(minStc1h))) return false
      // DI Spread filter (DI+ - DI-)
      if (minDiSpread || maxDiSpread) {
        const diP = fp2.di_plus_4h; const diM = fp2.di_minus_4h
        if (diP == null || diM == null) return false
        const spread = diP - diM
        if (minDiSpread && spread < parseFloat(minDiSpread)) return false
        if (maxDiSpread && spread > parseFloat(maxDiSpread)) return false
      }
      if (minAdxDim || maxAdxDim) {
        const adxV = fp2.adx_4h; const diM = fp2.di_minus_4h
        if (adxV != null && diM != null) {
          // Compare on rounded value to match what's displayed in the table
          const adxDim = Math.round(adxV - diM)
          if (minAdxDim && adxDim < parseFloat(minAdxDim)) return false
          if (maxAdxDim && adxDim > parseFloat(maxAdxDim)) return false
        }
      }
      // ─────── Tier 1+2 — new filters ───────
      const fpx = d.features_fingerprint || {}
      const adx = (d as any).alert_data || {}

      // Body % per TF (15m/30m/1h)
      const bodyChecks: [any, any, any][] = [
        [fpx.candle_15m_body_pct, minBody15m, maxBody15m],
        [fpx.candle_30m_body_pct, minBody30m, maxBody30m],
        [fpx.candle_1h_body_pct,  minBody1h,  maxBody1h],
      ]
      for (const [v, mn, mx] of bodyChecks) {
        if (mn !== '' && (v == null || v < parseFloat(mn))) return false
        if (mx !== '' && (v == null || v > parseFloat(mx))) return false
      }
      // Range % per TF
      const rangeChecks: [any, any, any][] = [
        [fpx.candle_15m_range_pct, minRange15m, maxRange15m],
        [fpx.candle_30m_range_pct, minRange30m, maxRange30m],
        [fpx.candle_1h_range_pct,  minRange1h,  maxRange1h],
      ]
      for (const [v, mn, mx] of rangeChecks) {
        if (mn !== '' && (v == null || v < parseFloat(mn))) return false
        if (mx !== '' && (v == null || v > parseFloat(mx))) return false
      }
      // Direction per TF
      if (dir15m !== 'ALL' && fpx.candle_15m_direction !== dir15m) return false
      if (dir30m !== 'ALL' && fpx.candle_30m_direction !== dir30m) return false
      if (dir1h  !== 'ALL' && fpx.candle_1h_direction  !== dir1h)  return false

      // Dominance ranges
      const domChecks: [any, any, any][] = [
        [fpx.btc_dominance, minBtcDom, maxBtcDom],
        [fpx.eth_dominance, minEthDom, maxEthDom],
        [fpx.others_d,      minOthersD, maxOthersD],
      ]
      for (const [v, mn, mx] of domChecks) {
        if (mn !== '' && (v == null || v < parseFloat(mn))) return false
        if (mx !== '' && (v == null || v > parseFloat(mx))) return false
      }
      // BTC/ETH 24h change
      const change24Checks: [any, any, any][] = [
        [fpx.btc_change_24h, minBtc24h, maxBtc24h],
        [fpx.eth_change_24h, minEth24h, maxEth24h],
      ]
      for (const [v, mn, mx] of change24Checks) {
        if (mn !== '' && (v == null || v < parseFloat(mn))) return false
        if (mx !== '' && (v == null || v > parseFloat(mx))) return false
      }
      // Volume USDT min
      if (minVolUsdt !== '' && (fpx.volume_usdt == null || fpx.volume_usdt < parseFloat(minVolUsdt))) return false
      // Accumulation hours
      if (minAccumH !== '' && (fpx.accumulation_hours == null || fpx.accumulation_hours < parseFloat(minAccumH))) return false
      if (maxAccumH !== '' && (fpx.accumulation_hours == null || fpx.accumulation_hours > parseFloat(maxAccumH))) return false
      // Quality axes count
      if (minQualityAxes !== '' && (fpx.quality_axes == null || fpx.quality_axes < parseInt(minQualityAxes))) return false
      // BTC season / ETH season
      if (btcSeasonFilter === 'YES' && !fpx.btc_season) return false
      if (btcSeasonFilter === 'NO' && fpx.btc_season) return false
      if (ethSeasonFilter === 'YES' && !fpx.eth_trend_bullish) return false  // proxy
      if (ethSeasonFilter === 'NO' && fpx.eth_trend_bullish) return false

      // ─── Tier 2 — alerts table ───
      // LazyBar 4H color
      if (lazy4hFilter.length > 0) {
        const lz4h = String(adx.lazy_4h || '').toLowerCase()
        const want = lazy4hFilter.map(c => c.toLowerCase())
        if (!want.some(c => lz4h.includes(c))) return false
      }
      // DMI cross 4H
      if (dmiCross4hFilter === 'YES' && !adx.dmi_cross_4h) return false
      if (dmiCross4hFilter === 'NO' && adx.dmi_cross_4h) return false
      // Bougie 4H validation
      if (bougie4hFilter === 'YES' && !adx.bougie_4h) return false
      if (bougie4hFilter === 'NO' && adx.bougie_4h) return false
      // Emotion
      if (emotionFilter.length > 0 && !emotionFilter.includes(String(adx.emotion || '').toUpperCase())) return false
      // RSI moves min per TF
      const rsiM = adx.rsi_moves || {}
      if (minRsiMv15m !== '' && (rsiM['15m'] == null || rsiM['15m'] < parseFloat(minRsiMv15m))) return false
      if (minRsiMv1h  !== '' && (rsiM['1h']  == null || rsiM['1h']  < parseFloat(minRsiMv1h)))  return false
      if (minRsiMv4h  !== '' && (rsiM['4h']  == null || rsiM['4h']  < parseFloat(minRsiMv4h)))  return false
      // DI+ moves min per TF
      const diPM = adx.di_plus_moves || {}
      if (minDiPMv15m !== '' && (diPM['15m'] == null || diPM['15m'] < parseFloat(minDiPMv15m))) return false
      if (minDiPMv1h  !== '' && (diPM['1h']  == null || diPM['1h']  < parseFloat(minDiPMv1h)))  return false
      if (minDiPMv4h  !== '' && (diPM['4h']  == null || diPM['4h']  < parseFloat(minDiPMv4h)))  return false
      // EC moves min per TF
      const ecM = adx.ec_moves || {}
      if (minEcMv15m !== '' && (ecM['15m'] == null || ecM['15m'] < parseFloat(minEcMv15m))) return false
      if (minEcMv1h  !== '' && (ecM['1h']  == null || ecM['1h']  < parseFloat(minEcMv1h)))  return false
      if (minEcMv4h  !== '' && (ecM['4h']  == null || ecM['4h']  < parseFloat(minEcMv4h)))  return false
      // Max profit potentiel (historic)
      if (minMaxProfit !== '' && (adx.max_profit_pct == null || adx.max_profit_pct < parseFloat(minMaxProfit))) return false
      if (maxMaxProfit !== '' && (adx.max_profit_pct == null || adx.max_profit_pct > parseFloat(maxMaxProfit))) return false
      // LazyBar color per TF
      const lzVals = adx.lazy_values || {}
      const lzColorAt = (tf: string): string => {
        const v = lzVals[tf]
        if (Array.isArray(v) && v.length >= 2) return String(v[1]).toLowerCase()
        if (typeof v === 'string') return v.toLowerCase()
        return ''
      }
      if (lazy15mFilter.length > 0) {
        const c = lzColorAt('15m')
        if (!lazy15mFilter.map(x => x.toLowerCase()).includes(c)) return false
      }
      if (lazy30mFilter.length > 0) {
        const c = lzColorAt('30m')
        if (!lazy30mFilter.map(x => x.toLowerCase()).includes(c)) return false
      }
      if (lazy1hFilter.length > 0) {
        const c = lzColorAt('1h')
        if (!lazy1hFilter.map(x => x.toLowerCase()).includes(c)) return false
      }

      // ─────── Tier 3 — analyze_alert structured features ───────
      if (minProgCount !== '' && (fpx.prog_count_effective == null || fpx.prog_count_effective < parseInt(minProgCount))) return false
      if (minBonusCount !== '' && (fpx.bonus_count == null || fpx.bonus_count < parseInt(minBonusCount))) return false
      if (fib4hF === 'YES' && !fpx.fib_4h_bonus) return false
      if (fib4hF === 'NO' && fpx.fib_4h_bonus) return false
      if (fib1hF === 'YES' && !fpx.fib_1h_bonus) return false
      if (fib1hF === 'NO' && fpx.fib_1h_bonus) return false
      if (vpPos1h.length > 0 && !vpPos1h.includes(String(fpx.vp_1h_position || ''))) return false
      if (vpPos4h.length > 0 && !vpPos4h.includes(String(fpx.vp_4h_position || ''))) return false
      if (obPos1h.length > 0 && !obPos1h.includes(String(fpx.ob_1h_position || ''))) return false
      if (obPos4h.length > 0 && !obPos4h.includes(String(fpx.ob_4h_position || ''))) return false
      if (obStrength1h.length > 0 && !obStrength1h.includes(String(fpx.ob_1h_strength || ''))) return false
      if (obStrength4h.length > 0 && !obStrength4h.includes(String(fpx.ob_4h_strength || ''))) return false
      if (obMitig1h === 'YES' && !fpx.ob_1h_mitigated) return false
      if (obMitig1h === 'NO' && fpx.ob_1h_mitigated) return false
      if (obMitig4h === 'YES' && !fpx.ob_4h_mitigated) return false
      if (obMitig4h === 'NO' && fpx.ob_4h_mitigated) return false
      if (fvgPos1h.length > 0 && !fvgPos1h.includes(String(fpx.fvg_1h_position || ''))) return false
      if (fvgPos4h.length > 0 && !fvgPos4h.includes(String(fpx.fvg_4h_position || ''))) return false
      if (macd1hTrend.length > 0 && !macd1hTrend.includes(String(fpx.macd_1h_trend || ''))) return false
      if (macd4hTrend.length > 0 && !macd4hTrend.includes(String(fpx.macd_4h_trend || ''))) return false
      if (macd1hGrow === 'YES' && !fpx.macd_1h_growing) return false
      if (macd1hGrow === 'NO' && fpx.macd_1h_growing) return false
      if (macd4hGrow === 'YES' && !fpx.macd_4h_growing) return false
      if (macd4hGrow === 'NO' && fpx.macd_4h_growing) return false
      if (bb1hSqueeze === 'YES' && !fpx.bb_1h_squeeze) return false
      if (bb1hSqueeze === 'NO' && fpx.bb_1h_squeeze) return false
      if (bb4hSqueeze === 'YES' && !fpx.bb_4h_squeeze) return false
      if (bb4hSqueeze === 'NO' && fpx.bb_4h_squeeze) return false
      if (stoch1hZone.length > 0 && !stoch1hZone.includes(String(fpx.stochrsi_1h_zone || ''))) return false
      if (stoch4hZone.length > 0 && !stoch4hZone.includes(String(fpx.stochrsi_4h_zone || ''))) return false
      if (minEmaStack1h !== '' && (fpx.ema_stack_1h_count == null || fpx.ema_stack_1h_count < parseInt(minEmaStack1h))) return false
      if (minEmaStack4h !== '' && (fpx.ema_stack_4h_count == null || fpx.ema_stack_4h_count < parseInt(minEmaStack4h))) return false
      if (minAdx1h !== '' && (fpx.adx_1h == null || fpx.adx_1h < parseFloat(minAdx1h))) return false
      if (maxAdx1h !== '' && (fpx.adx_1h == null || fpx.adx_1h > parseFloat(maxAdx1h))) return false
      if (minRsiMtf !== '' && (fpx.rsi_mtf_aligned_count == null || fpx.rsi_mtf_aligned_count < parseInt(minRsiMtf))) return false
      if (minMlScore !== '' && (fpx.ml_p_success == null || fpx.ml_p_success < parseFloat(minMlScore))) return false

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
        case 'adx_minus_dim': va = (fp_a.adx_4h || 0) - (fp_a.di_minus_4h || 0); vb = (fp_b.adx_4h || 0) - (fp_b.di_minus_4h || 0); break
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
        // ─── Tier 3 sort cases ───
        case 'prog':     va = fp_a.prog_count_effective ?? -1; vb = fp_b.prog_count_effective ?? -1; break
        case 'bonus_n':  va = fp_a.bonus_count ?? -1;          vb = fp_b.bonus_count ?? -1; break
        case 'fib4h':    va = fp_a.fib_4h_bonus ? 1 : 0;       vb = fp_b.fib_4h_bonus ? 1 : 0; break
        case 'fib1h':    va = fp_a.fib_1h_bonus ? 1 : 0;       vb = fp_b.fib_1h_bonus ? 1 : 0; break
        case 'vp4h': {
          const m: Record<string, number> = { ABOVE_VAH: 2, IN_VA: 1, BELOW_VAL: 0 }
          va = m[String(fp_a.vp_4h_position || '')] ?? -1; vb = m[String(fp_b.vp_4h_position || '')] ?? -1; break
        }
        case 'vp1h': {
          const m: Record<string, number> = { ABOVE_VAH: 2, IN_VA: 1, BELOW_VAL: 0 }
          va = m[String(fp_a.vp_1h_position || '')] ?? -1; vb = m[String(fp_b.vp_1h_position || '')] ?? -1; break
        }
        case 'ob4h': {
          const pos: Record<string, number> = { ABOVE: 3, INSIDE: 2, BELOW: 1 }
          const str: Record<string, number> = { STRONG: 30, MEDIUM: 20, WEAK: 10 }
          va = (pos[String(fp_a.ob_4h_position || '')] ?? 0) + (str[String(fp_a.ob_4h_strength || '')] ?? 0)
          vb = (pos[String(fp_b.ob_4h_position || '')] ?? 0) + (str[String(fp_b.ob_4h_strength || '')] ?? 0)
          break
        }
        case 'ob1h': {
          const pos: Record<string, number> = { ABOVE: 3, INSIDE: 2, BELOW: 1 }
          const str: Record<string, number> = { STRONG: 30, MEDIUM: 20, WEAK: 10 }
          va = (pos[String(fp_a.ob_1h_position || '')] ?? 0) + (str[String(fp_a.ob_1h_strength || '')] ?? 0)
          vb = (pos[String(fp_b.ob_1h_position || '')] ?? 0) + (str[String(fp_b.ob_1h_strength || '')] ?? 0)
          break
        }
        case 'macd4h':   va = fp_a.macd_4h_trend === 'BULLISH' ? (fp_a.macd_4h_growing ? 2 : 1) : -1
                         vb = fp_b.macd_4h_trend === 'BULLISH' ? (fp_b.macd_4h_growing ? 2 : 1) : -1; break
        case 'macd1h':   va = fp_a.macd_1h_trend === 'BULLISH' ? (fp_a.macd_1h_growing ? 2 : 1) : -1
                         vb = fp_b.macd_1h_trend === 'BULLISH' ? (fp_b.macd_1h_growing ? 2 : 1) : -1; break
        case 'stoch4h': {
          const m: Record<string, number> = { OVERSOLD: 2, NEUTRAL: 1, OVERBOUGHT: 0 }
          va = m[String(fp_a.stochrsi_4h_zone || '')] ?? -1; vb = m[String(fp_b.stochrsi_4h_zone || '')] ?? -1; break
        }
        case 'stoch1h': {
          const m: Record<string, number> = { OVERSOLD: 2, NEUTRAL: 1, OVERBOUGHT: 0 }
          va = m[String(fp_a.stochrsi_1h_zone || '')] ?? -1; vb = m[String(fp_b.stochrsi_1h_zone || '')] ?? -1; break
        }
        case 'ema_st4h': va = fp_a.ema_stack_4h_count ?? -1; vb = fp_b.ema_stack_4h_count ?? -1; break
        case 'ema_st1h': va = fp_a.ema_stack_1h_count ?? -1; vb = fp_b.ema_stack_1h_count ?? -1; break
        case 'bb4h':     va = fp_a.bb_4h_squeeze ? 1 : 0; vb = fp_b.bb_4h_squeeze ? 1 : 0; break
        case 'fvg4h': {
          const m: Record<string, number> = { ABOVE: 2, INSIDE: 1, BELOW: 0 }
          va = m[String(fp_a.fvg_4h_position || '')] ?? -1; vb = m[String(fp_b.fvg_4h_position || '')] ?? -1; break
        }
        case 'adx1h':    va = fp_a.adx_1h ?? -1; vb = fp_b.adx_1h ?? -1; break
        case 'rsi_mtf':  va = fp_a.rsi_mtf_aligned_count ?? -1; vb = fp_b.rsi_mtf_aligned_count ?? -1; break
        case 'ml':       va = fp_a.ml_p_success ?? -1; vb = fp_b.ml_p_success ?? -1; break

        case 'timestamp':
          va = a.alert_data?.alert_timestamp || a.timestamp || ''
          vb = b.alert_data?.alert_timestamp || b.timestamp || ''
          break
        default: {
          // Prefer the underlying alert fire time; fallback to decision timestamp.
          // This keeps backfilled analyses in their real chronological slot.
          va = a.alert_data?.alert_timestamp || a.timestamp || ''
          vb = b.alert_data?.alert_timestamp || b.timestamp || ''
        }
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      // Tiebreaker: most recent alert fire time, then id — guarantees newest-first stability
      const ta = a.alert_data?.alert_timestamp || a.timestamp || ''
      const tb = b.alert_data?.alert_timestamp || b.timestamp || ''
      if (ta !== tb) return ta < tb ? 1 : -1
      const ia = a.id || ''; const ib = b.id || ''
      return ia < ib ? 1 : ia > ib ? -1 : 0
    })

    return result
  }, [decisions, pairSearch, decisionFilter, outcomeFilter, vipFilter, v4GateFilter, v4MinScore, v4AllowVip, v4AllowHt, v4AllowNoVip, v4CandleDir, gradeFilter, dateFrom, dateTo, minConf, maxConf, minPnl, maxPnl, minScore, minAccum, maxAccum, minDiPlus, maxDiPlus, minDiMinus, maxDiMinus, minAdx, maxAdx, minRsi, maxRsi, ppFilter, ecFilter, tfFilter, minPuissance, minVolPct, maxVolPct, condFilters, minChange24h, maxChange24h, minBody4h, maxBody4h, minRange4h, maxRange4h, dirFilter, fgFilter, btcTrendFilter, ethTrendFilter, altSeasonFilter, minVol1h, minVol4h, minVol24h, minVol48h, maxVol1h, maxVol4h, maxVol24h, maxVol48h, excludeAllRedVol, excludeGrayIndicators, maxStc15m, maxStc30m, maxStc1h, minStc15m, minStc30m, minStc1h, minTfBody, minDiSpread, maxDiSpread, minAdxDim, maxAdxDim, v8v9AllMode,
      // Tier 1+2 new filters
      minBody15m, maxBody15m, minBody30m, maxBody30m, minBody1h, maxBody1h,
      minRange15m, maxRange15m, minRange30m, maxRange30m, minRange1h, maxRange1h,
      dir15m, dir30m, dir1h,
      minBtcDom, maxBtcDom, minEthDom, maxEthDom, minOthersD, maxOthersD,
      minBtc24h, maxBtc24h, minEth24h, maxEth24h,
      minVolUsdt, minAccumH, maxAccumH, minQualityAxes,
      btcSeasonFilter, ethSeasonFilter,
      lazy4hFilter, dmiCross4hFilter, bougie4hFilter, emotionFilter,
      minRsiMv15m, minRsiMv1h, minRsiMv4h,
      minDiPMv15m, minDiPMv1h, minDiPMv4h,
      minEcMv15m, minEcMv1h, minEcMv4h,
      minMaxProfit, maxMaxProfit,
      lazy15mFilter, lazy30mFilter, lazy1hFilter,
      // Tier 3 deps
      minProgCount, minBonusCount, fib4hF, fib1hF,
      vpPos1h, vpPos4h, obPos1h, obPos4h, obStrength1h, obStrength4h, obMitig1h, obMitig4h,
      fvgPos1h, fvgPos4h,
      macd1hTrend, macd4hTrend, macd1hGrow, macd4hGrow,
      bb1hSqueeze, bb4hSqueeze,
      stoch1hZone, stoch4hZone,
      minEmaStack1h, minEmaStack4h,
      minAdx1h, maxAdx1h, minRsiMtf, minMlScore,
      sortKey, sortDir])

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

  useEffect(() => { setCurrentPage(1) }, [pairSearch, decisionFilter, outcomeFilter, vipFilter, v4GateFilter])

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

            {/* V4 Gate Filter — configurable V4 strategy gate */}
            <div className="flex flex-col gap-1.5 px-2 py-1.5 rounded-lg border border-amber-500/20 bg-amber-500/5">
              <div className="flex items-center gap-1.5">
                <span className="text-amber-400 text-sm">🛡️</span>
                <span className="text-[11px] font-semibold text-amber-300 mr-1">V4 Gate</span>
                {['ALL', 'PASS', 'REJECT'].map(v => (
                  <button
                    key={v}
                    onClick={() => setV4GateFilter(v)}
                    className={cn(
                      "px-2.5 py-1 rounded text-[11px] font-medium transition-colors border",
                      v4GateFilter === v
                        ? v === 'ALL' ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                          : v === 'PASS' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                          : 'bg-red-500/20 border-red-500/40 text-red-300'
                        : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
                    )}
                  >
                    {v === 'ALL' ? 'Tous' : v === 'PASS' ? '✅ Pass' : '❌ Reject'}
                  </button>
                ))}
              </div>
              {v4GateFilter !== 'ALL' && (
                <div className="flex flex-wrap items-center gap-2 text-[11px]">
                  {/* Min score */}
                  <label className="flex items-center gap-1 text-gray-400">
                    Score≥
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={v4MinScore}
                      onChange={e => setV4MinScore(Math.max(1, Math.min(10, parseInt(e.target.value) || 0)))}
                      className="w-12 px-1.5 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center"
                    />
                  </label>
                  {/* VIP types */}
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400">VIP types:</span>
                  {[
                    { key: 'vip', label: '⭐ VIP', state: v4AllowVip, set: setV4AllowVip },
                    { key: 'ht', label: '🏆 HT', state: v4AllowHt, set: setV4AllowHt },
                    { key: 'novip', label: 'No VIP', state: v4AllowNoVip, set: setV4AllowNoVip },
                  ].map(opt => (
                    <button
                      key={opt.key}
                      onClick={() => opt.set(!opt.state)}
                      className={cn(
                        "px-2 py-0.5 rounded border",
                        opt.state
                          ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300'
                      )}
                    >
                      {opt.state ? '✓ ' : ''}{opt.label}
                    </button>
                  ))}
                  {/* 4H candle direction */}
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400">4H:</span>
                  {([
                    { key: 'green', label: '🟢 Green', color: 'emerald' },
                    { key: 'red', label: '🔴 Red', color: 'red' },
                    { key: 'any', label: 'Any', color: 'gray' },
                  ] as const).map(opt => (
                    <button
                      key={opt.key}
                      onClick={() => setV4CandleDir(opt.key)}
                      className={cn(
                        "px-2 py-0.5 rounded border",
                        v4CandleDir === opt.key
                          ? opt.color === 'emerald' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                            : opt.color === 'red' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                            : 'bg-gray-600/20 border-gray-500/40 text-gray-300'
                          : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300'
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                  {/* Reset to defaults */}
                  <button
                    onClick={() => {
                      setV4MinScore(8); setV4AllowVip(true); setV4AllowHt(true);
                      setV4AllowNoVip(false); setV4CandleDir('green')
                    }}
                    className="px-2 py-0.5 rounded border border-gray-700 bg-gray-800 text-gray-500 hover:text-gray-300"
                    title="Reset aux valeurs V4 par défaut"
                  >
                    ↺ V4 défaut
                  </button>
                </div>
              )}
            </div>

            {(pairSearch || decisionFilter !== 'ALL' || outcomeFilter !== 'ALL' || vipFilter !== 'ALL' || v4GateFilter !== 'ALL') && (
              <button
                onClick={() => { setPairSearch(''); setDecisionFilter('ALL'); setOutcomeFilter('ALL'); setVipFilter('ALL'); setV4GateFilter('ALL'); setGradeFilter([]); setDateFrom(''); setDateTo(''); setMinConf(''); setMaxConf(''); setMinPnl(''); setMaxPnl(''); setMinScore(''); setMinAccum(''); setMaxAccum(''); setMinDiPlus(''); setMaxDiPlus(''); setMinDiMinus(''); setMaxDiMinus(''); setMinAdx(''); setMaxAdx(''); setMinRsi(''); setMaxRsi(''); setPpFilter('ALL'); setEcFilter('ALL'); setTfFilter([]); setMinPuissance(''); setMinVolPct(''); setMaxVolPct(''); setCondFilters([]); setMinChange24h(''); setMaxChange24h(''); setMinBody4h(''); setMaxBody4h(''); setMinRange4h(''); setMaxRange4h(''); setDirFilter('ALL'); setFgFilter([]); setBtcTrendFilter('ALL'); setEthTrendFilter('ALL'); setAltSeasonFilter('ALL'); setMinVol1h(''); setMinVol4h(''); setMinVol24h(''); setMinVol48h(''); setMinDiSpread(''); setMaxDiSpread(''); setMaxStc15m(''); setMaxStc30m(''); setMaxStc1h(''); setMinTfBody(''); setV8v9AllMode(false);
                  // Tier 1+2 reset
                  setMinBody15m(''); setMaxBody15m(''); setMinBody30m(''); setMaxBody30m(''); setMinBody1h(''); setMaxBody1h('');
                  setMinRange15m(''); setMaxRange15m(''); setMinRange30m(''); setMaxRange30m(''); setMinRange1h(''); setMaxRange1h('');
                  setDir15m('ALL'); setDir30m('ALL'); setDir1h('ALL');
                  setMinBtcDom(''); setMaxBtcDom(''); setMinEthDom(''); setMaxEthDom(''); setMinOthersD(''); setMaxOthersD('');
                  setMinBtc24h(''); setMaxBtc24h(''); setMinEth24h(''); setMaxEth24h('');
                  setMinVolUsdt(''); setMinAccumH(''); setMaxAccumH(''); setMinQualityAxes('');
                  setBtcSeasonFilter('ALL'); setEthSeasonFilter('ALL');
                  setLazy4hFilter([]); setDmiCross4hFilter('ALL'); setBougie4hFilter('ALL'); setEmotionFilter([]);
                  setMinRsiMv15m(''); setMinRsiMv1h(''); setMinRsiMv4h('');
                  setMinDiPMv15m(''); setMinDiPMv1h(''); setMinDiPMv4h('');
                  setMinEcMv15m(''); setMinEcMv1h(''); setMinEcMv4h('');
                  setMinMaxProfit(''); setMaxMaxProfit('');
                  setLazy15mFilter([]); setLazy30mFilter([]); setLazy1hFilter([]);
                  // Tier 3 reset
                  setMinProgCount(''); setMinBonusCount(''); setFib4hF('ALL'); setFib1hF('ALL');
                  setVpPos1h([]); setVpPos4h([]); setObPos1h([]); setObPos4h([]);
                  setObStrength1h([]); setObStrength4h([]); setObMitig1h('ALL'); setObMitig4h('ALL');
                  setFvgPos1h([]); setFvgPos4h([]);
                  setMacd1hTrend([]); setMacd4hTrend([]); setMacd1hGrow('ALL'); setMacd4hGrow('ALL');
                  setBb1hSqueeze('ALL'); setBb4hSqueeze('ALL');
                  setStoch1hZone([]); setStoch4hZone([]);
                  setMinEmaStack1h(''); setMinEmaStack4h('');
                  setMinAdx1h(''); setMaxAdx1h(''); setMinRsiMtf(''); setMinMlScore('');
                }}
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
                <input type="number" step="0.1" placeholder="0" value={minBody4h} onChange={e => setMinBody4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Body 4H max %</label>
                <input type="number" step="0.1" placeholder="100" value={maxBody4h} onChange={e => setMaxBody4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Range 4H min %</label>
                <input type="number" step="0.1" placeholder="0" value={minRange4h} onChange={e => setMinRange4h(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Range 4H max %</label>
                <input type="number" step="0.1" placeholder="100" value={maxRange4h} onChange={e => setMaxRange4h(e.target.value)}
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
                <label className="text-[10px] text-gray-500 uppercase">ADX − DI− min/max</label>
                <div className="flex gap-1">
                  <input type="number" placeholder="min" value={minAdxDim} onChange={e => setMinAdxDim(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" placeholder="max" value={maxAdxDim} onChange={e => setMaxAdxDim(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 1H min/max %</label>
                <div className="flex gap-1">
                  <input type="number" placeholder="min" value={minVol1h} onChange={e => setMinVol1h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" placeholder="max" value={maxVol1h} onChange={e => setMaxVol1h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 4H min/max %</label>
                <div className="flex gap-1">
                  <input type="number" placeholder="min" value={minVol4h} onChange={e => setMinVol4h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" placeholder="max" value={maxVol4h} onChange={e => setMaxVol4h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 24H min/max %</label>
                <div className="flex gap-1">
                  <input type="number" placeholder="min" value={minVol24h} onChange={e => setMinVol24h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" placeholder="max" value={maxVol24h} onChange={e => setMaxVol24h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Vol Spike 48H min/max %</label>
                <div className="flex gap-1">
                  <input type="number" placeholder="min" value={minVol48h} onChange={e => setMinVol48h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" placeholder="max" value={maxVol48h} onChange={e => setMaxVol48h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Exclure vol tout rouge</label>
                <label className="flex items-center gap-2 mt-1 cursor-pointer px-2 py-1.5 bg-gray-800 border border-gray-700 rounded hover:border-red-500/40">
                  <input type="checkbox" checked={excludeAllRedVol} onChange={e => setExcludeAllRedVol(e.target.checked)}
                    className="w-3.5 h-3.5 accent-red-500" />
                  <span className="text-[10px] text-gray-300">V1h+V4h+V24h+V48h tous &lt; 0</span>
                </label>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">Exclure si 4+ indices gris</label>
                <label className="flex items-center gap-2 mt-1 cursor-pointer px-2 py-1.5 bg-gray-800 border border-gray-700 rounded hover:border-gray-400/40">
                  <input type="checkbox" checked={excludeGrayIndicators} onChange={e => setExcludeGrayIndicators(e.target.checked)}
                    className="w-3.5 h-3.5 accent-gray-400" />
                  <span className="text-[10px] text-gray-300">DI+ / DI- / ADX / D± / RSI (4+ neutres)</span>
                </label>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">TF Body min %</label>
                <input type="number" step="0.5" placeholder="0" value={minTfBody} onChange={e => setMinTfBody(e.target.value)}
                  className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">STC 15m min/max</label>
                <div className="flex gap-1">
                  <input type="number" step="0.1" placeholder="min" value={minStc15m} onChange={e => setMinStc15m(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" step="0.1" placeholder="max" value={maxStc15m} onChange={e => setMaxStc15m(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">STC 30m min/max</label>
                <div className="flex gap-1">
                  <input type="number" step="0.1" placeholder="min" value={minStc30m} onChange={e => setMinStc30m(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" step="0.1" placeholder="max" value={maxStc30m} onChange={e => setMaxStc30m(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase">STC 1h min/max</label>
                <div className="flex gap-1">
                  <input type="number" step="0.1" placeholder="min" value={minStc1h} onChange={e => setMinStc1h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                  <input type="number" step="0.1" placeholder="max" value={maxStc1h} onChange={e => setMaxStc1h(e.target.value)}
                    className="w-1/2 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500" />
                </div>
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
              const pending = filtered.filter(d => d.outcome === 'PENDING' || d.outcome == null).length
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
                    <div className="text-[10px] text-gray-600">{wins}W/{losses}L<span className="text-gray-500"> · {pending}P</span></div>
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
          {/* ════ NEW: Tier 1+2 indicator filters ════ */}
          <div className="bg-gray-900/30 border border-gray-800 rounded-xl p-3 space-y-3">
            <div className="text-[11px] font-semibold text-cyan-300">📊 Indicateurs supplémentaires</div>

            {/* Body/Range/Direction per TF */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400 mr-1">🕯 Body% :</span>
              {[['15m', minBody15m, setMinBody15m, maxBody15m, setMaxBody15m],
                ['30m', minBody30m, setMinBody30m, maxBody30m, setMaxBody30m],
                ['1h',  minBody1h,  setMinBody1h,  maxBody1h,  setMaxBody1h]].map(([tf, mn, smn, mx, smx]: any) => (
                <span key={tf} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{tf}</span>
                  <input type="number" step="0.1" placeholder="min" value={mn} onChange={e => smn(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                  <input type="number" step="0.1" placeholder="max" value={mx} onChange={e => smx(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                </span>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400 mr-1">📏 Range% :</span>
              {[['15m', minRange15m, setMinRange15m, maxRange15m, setMaxRange15m],
                ['30m', minRange30m, setMinRange30m, maxRange30m, setMaxRange30m],
                ['1h',  minRange1h,  setMinRange1h,  maxRange1h,  setMaxRange1h]].map(([tf, mn, smn, mx, smx]: any) => (
                <span key={tf} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{tf}</span>
                  <input type="number" step="0.1" placeholder="min" value={mn} onChange={e => smn(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                  <input type="number" step="0.1" placeholder="max" value={mx} onChange={e => smx(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                </span>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">🎨 Direction :</span>
              {[['15m', dir15m, setDir15m], ['30m', dir30m, setDir30m], ['1h', dir1h, setDir1h]].map(([tf, val, setter]: any) => (
                <span key={tf} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{tf}</span>
                  {(['ALL', 'green', 'red'] as const).map(opt => (
                    <button key={opt} onClick={() => setter(opt)} className={cn("px-1.5 py-0.5 rounded border", val === opt
                      ? opt === 'green' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                        : opt === 'red' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                        : 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                      : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>
                      {opt === 'ALL' ? 'all' : opt === 'green' ? '🟢' : '🔴'}
                    </button>
                  ))}
                </span>
              ))}
            </div>

            {/* Market dominance + 24h changes */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400 mr-1">🌍 Dom% :</span>
              {[['BTC', minBtcDom, setMinBtcDom, maxBtcDom, setMaxBtcDom],
                ['ETH', minEthDom, setMinEthDom, maxEthDom, setMaxEthDom],
                ['Oth', minOthersD, setMinOthersD, maxOthersD, setMaxOthersD]].map(([lbl, mn, smn, mx, smx]: any) => (
                <span key={lbl} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{lbl}</span>
                  <input type="number" step="0.1" placeholder="min" value={mn} onChange={e => smn(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                  <input type="number" step="0.1" placeholder="max" value={mx} onChange={e => smx(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                </span>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400 mr-1">24h Δ :</span>
              {[['BTC', minBtc24h, setMinBtc24h, maxBtc24h, setMaxBtc24h],
                ['ETH', minEth24h, setMinEth24h, maxEth24h, setMaxEth24h]].map(([lbl, mn, smn, mx, smx]: any) => (
                <span key={lbl} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{lbl}</span>
                  <input type="number" step="0.1" placeholder="min" value={mn} onChange={e => smn(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                  <input type="number" step="0.1" placeholder="max" value={mx} onChange={e => smx(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                </span>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">Vol $≥</span>
              <input type="number" step="1000" placeholder="min" value={minVolUsdt} onChange={e => setMinVolUsdt(e.target.value)} className="w-20 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
            </div>

            {/* Accumulation hours + Quality axes + season toggles */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">⏱ Accum heures :</span>
              <input type="number" placeholder="min" value={minAccumH} onChange={e => setMinAccumH(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
              <input type="number" placeholder="max" value={maxAccumH} onChange={e => setMaxAccumH(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">📐 Quality axes ≥</span>
              <input type="number" min="0" max="5" placeholder="0-5" value={minQualityAxes} onChange={e => setMinQualityAxes(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">BTC season :</span>
              {(['ALL', 'YES', 'NO'] as const).map(o => (
                <button key={o} onClick={() => setBtcSeasonFilter(o)} className={cn("px-1.5 py-0.5 rounded border", btcSeasonFilter === o ? 'bg-orange-500/20 border-orange-500/40 text-orange-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>{o.toLowerCase()}</button>
              ))}
              <span className="text-gray-400">ETH bull :</span>
              {(['ALL', 'YES', 'NO'] as const).map(o => (
                <button key={o} onClick={() => setEthSeasonFilter(o)} className={cn("px-1.5 py-0.5 rounded border", ethSeasonFilter === o ? 'bg-blue-500/20 border-blue-500/40 text-blue-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>{o.toLowerCase()}</button>
              ))}
            </div>

            {/* Tracker fields: emotion, dmi cross 4h, bougie 4h, max profit */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">🎯 Emotion :</span>
              {['STRONG', 'NEUTRAL', 'WEAK'].map(e => (
                <button key={e} onClick={() => setEmotionFilter(emotionFilter.includes(e) ? emotionFilter.filter(x => x !== e) : [...emotionFilter, e])} className={cn("px-1.5 py-0.5 rounded border", emotionFilter.includes(e) ? 'bg-pink-500/20 border-pink-500/40 text-pink-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>{e.toLowerCase()}</button>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">⚔️ DMI cross 4H :</span>
              {(['ALL', 'YES', 'NO'] as const).map(o => (
                <button key={o} onClick={() => setDmiCross4hFilter(o)} className={cn("px-1.5 py-0.5 rounded border", dmiCross4hFilter === o ? 'bg-red-500/20 border-red-500/40 text-red-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>{o.toLowerCase()}</button>
              ))}
              <span className="text-gray-400">🟢 Bougie 4H :</span>
              {(['ALL', 'YES', 'NO'] as const).map(o => (
                <button key={o} onClick={() => setBougie4hFilter(o)} className={cn("px-1.5 py-0.5 rounded border", bougie4hFilter === o ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>{o.toLowerCase()}</button>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">📈 Max profit% :</span>
              <input type="number" step="0.5" placeholder="min" value={minMaxProfit} onChange={e => setMinMaxProfit(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
              <input type="number" step="0.5" placeholder="max" value={maxMaxProfit} onChange={e => setMaxMaxProfit(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
            </div>

            {/* LazyBar colors per TF */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400 mr-1">⚡ LazyBar :</span>
              {[['4H', lazy4hFilter, setLazy4hFilter],
                ['1h', lazy1hFilter, setLazy1hFilter],
                ['30m', lazy30mFilter, setLazy30mFilter],
                ['15m', lazy15mFilter, setLazy15mFilter]].map(([tf, val, setter]: any) => (
                <span key={tf} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{tf}</span>
                  {[['Red', 'red'], ['Yellow', 'yellow'], ['Green', 'green'], ['Navy', 'navy']].map(([lbl, color]) => {
                    const active = val.includes(lbl)
                    const colorCls = color === 'red' ? 'bg-red-500/20 border-red-500/40 text-red-300'
                      : color === 'yellow' ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300'
                      : color === 'green' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                      : 'bg-blue-500/20 border-blue-500/40 text-blue-300'
                    return (
                      <button key={lbl} onClick={() => setter(active ? val.filter((x: string) => x !== lbl) : [...val, lbl])}
                        className={cn("px-1 py-0.5 rounded border", active ? colorCls : 'bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300')}>
                        {lbl[0]}
                      </button>
                    )
                  })}
                </span>
              ))}
            </div>

            {/* Moves per TF: RSI, DI+, EC */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400 mr-1">📊 Moves min :</span>
              {[['RSI', minRsiMv15m, setMinRsiMv15m, minRsiMv1h, setMinRsiMv1h, minRsiMv4h, setMinRsiMv4h],
                ['DI+', minDiPMv15m, setMinDiPMv15m, minDiPMv1h, setMinDiPMv1h, minDiPMv4h, setMinDiPMv4h],
                ['EC',  minEcMv15m, setMinEcMv15m, minEcMv1h, setMinEcMv1h, minEcMv4h, setMinEcMv4h]].map(([lbl, v15, s15, v1h, s1h, v4h, s4h]: any) => (
                <span key={lbl} className="flex items-center gap-0.5">
                  <span className="text-gray-500">{lbl}:</span>
                  <input type="number" step="1" placeholder="15m" value={v15} onChange={e => s15(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                  <input type="number" step="1" placeholder="1h"  value={v1h} onChange={e => s1h(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                  <input type="number" step="1" placeholder="4h"  value={v4h} onChange={e => s4h(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
                </span>
              ))}
            </div>
          </div>

          {/* ════ Tier 3 — analyze_alert structured features ════ */}
          <div className="bg-gray-900/30 border border-fuchsia-900/40 rounded-xl p-3 space-y-3">
            <div className="text-[11px] font-semibold text-fuchsia-300">🔬 Indicateurs analyse OpenClaw <span className="text-gray-500 font-normal">(disponibles à partir de 26/04 — alertes plus anciennes : champs vides)</span></div>

            {/* Progressive conditions + bonus count + ADX 1H + RSI MTF + ML */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">⚙️ Prog cond ≥</span>
              <input type="number" min="0" max="5" placeholder="0-5" value={minProgCount} onChange={e => setMinProgCount(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">🎁 Bonus ≥</span>
              <input type="number" min="0" max="23" placeholder="0-23" value={minBonusCount} onChange={e => setMinBonusCount(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">ADX 1H</span>
              <input type="number" placeholder="min" value={minAdx1h} onChange={e => setMinAdx1h(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
              <input type="number" placeholder="max" value={maxAdx1h} onChange={e => setMaxAdx1h(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">RSI MTF aligned ≥</span>
              <input type="number" min="0" max="3" placeholder="0-3" value={minRsiMtf} onChange={e => setMinRsiMtf(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">🤖 ML p_success ≥</span>
              <input type="number" step="0.05" min="0" max="1" placeholder="0-1" value={minMlScore} onChange={e => setMinMlScore(e.target.value)} className="w-14 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200" />
            </div>

            {/* Fibonacci + BB squeeze + MACD growing */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">🔢 Fib :</span>
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'f4-'+o} onClick={() => setFib4hF(o)} className={cn("px-1.5 py-0.5 rounded border", fib4hF === o ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>4H:{o.toLowerCase()}</button>
              ))}
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'f1-'+o} onClick={() => setFib1hF(o)} className={cn("px-1.5 py-0.5 rounded border", fib1hF === o ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>1H:{o.toLowerCase()}</button>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">📊 BB squeeze :</span>
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'bb1-'+o} onClick={() => setBb1hSqueeze(o)} className={cn("px-1.5 py-0.5 rounded border", bb1hSqueeze === o ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>1H:{o.toLowerCase()}</button>
              ))}
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'bb4-'+o} onClick={() => setBb4hSqueeze(o)} className={cn("px-1.5 py-0.5 rounded border", bb4hSqueeze === o ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>4H:{o.toLowerCase()}</button>
              ))}
            </div>

            {/* MACD trend + StochRSI zone */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">📈 MACD trend :</span>
              {(['1h', '4h'] as const).map(tf => {
                const val = tf === '1h' ? macd1hTrend : macd4hTrend
                const setter = tf === '1h' ? setMacd1hTrend : setMacd4hTrend
                return ['BULLISH','BEARISH'].map(t => {
                  const active = val.includes(t)
                  return (
                    <button key={`m-${tf}-${t}`} onClick={() => setter(active ? val.filter(x => x !== t) : [...val, t])}
                      className={cn("px-1.5 py-0.5 rounded border", active ? (t === 'BULLISH' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' : 'bg-red-500/20 border-red-500/40 text-red-300') : 'bg-gray-800 border-gray-700 text-gray-500')}>
                      {tf}:{t === 'BULLISH' ? '🟢' : '🔴'}
                    </button>
                  )
                })
              })}
              <span className="text-gray-400">grow:</span>
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'mg1-'+o} onClick={() => setMacd1hGrow(o)} className={cn("px-1.5 py-0.5 rounded border", macd1hGrow === o ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>1H:{o.toLowerCase()}</button>
              ))}
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'mg4-'+o} onClick={() => setMacd4hGrow(o)} className={cn("px-1.5 py-0.5 rounded border", macd4hGrow === o ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>4H:{o.toLowerCase()}</button>
              ))}
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">🌊 StochRSI :</span>
              {(['1h', '4h'] as const).map(tf => {
                const val = tf === '1h' ? stoch1hZone : stoch4hZone
                const setter = tf === '1h' ? setStoch1hZone : setStoch4hZone
                return ['OVERSOLD','NEUTRAL','OVERBOUGHT'].map(z => {
                  const active = val.includes(z)
                  return (
                    <button key={`s-${tf}-${z}`} onClick={() => setter(active ? val.filter(x => x !== z) : [...val, z])}
                      className={cn("px-1.5 py-0.5 rounded border", active ? (z === 'OVERSOLD' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300' : z === 'OVERBOUGHT' ? 'bg-red-500/20 border-red-500/40 text-red-300' : 'bg-gray-700/50 border-gray-600 text-gray-300') : 'bg-gray-800 border-gray-700 text-gray-500')}>
                      {tf}:{z === 'OVERSOLD' ? '⬇' : z === 'OVERBOUGHT' ? '⬆' : '➖'}
                    </button>
                  )
                })
              })}
            </div>

            {/* EMA Stack count + Volume Profile position */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">🪜 EMA Stack ≥ :</span>
              <span className="text-gray-500">1H</span>
              <input type="number" min="0" max="4" placeholder="0-4" value={minEmaStack1h} onChange={e => setMinEmaStack1h(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center" />
              <span className="text-gray-500">4H</span>
              <input type="number" min="0" max="4" placeholder="0-4" value={minEmaStack4h} onChange={e => setMinEmaStack4h(e.target.value)} className="w-12 px-1 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-200 text-center" />
              <span className="text-gray-600">|</span>
              <span className="text-gray-400">🏦 VP pos :</span>
              {(['1h', '4h'] as const).map(tf => {
                const val = tf === '1h' ? vpPos1h : vpPos4h
                const setter = tf === '1h' ? setVpPos1h : setVpPos4h
                return ['IN_VA','ABOVE_VAH','BELOW_VAL'].map(p => {
                  const active = val.includes(p)
                  return (
                    <button key={`vp-${tf}-${p}`} onClick={() => setter(active ? val.filter(x => x !== p) : [...val, p])}
                      className={cn("px-1.5 py-0.5 rounded border", active ? 'bg-purple-500/20 border-purple-500/40 text-purple-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>
                      {tf}:{p === 'IN_VA' ? 'IN' : p === 'ABOVE_VAH' ? '↑' : '↓'}
                    </button>
                  )
                })
              })}
            </div>

            {/* Order Blocks — position + strength + mitigated */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">🧱 OB pos :</span>
              {(['1h', '4h'] as const).map(tf => {
                const val = tf === '1h' ? obPos1h : obPos4h
                const setter = tf === '1h' ? setObPos1h : setObPos4h
                return ['ABOVE','INSIDE','BELOW'].map(p => {
                  const active = val.includes(p)
                  return (
                    <button key={`ob-${tf}-${p}`} onClick={() => setter(active ? val.filter(x => x !== p) : [...val, p])}
                      className={cn("px-1.5 py-0.5 rounded border", active ? 'bg-orange-500/20 border-orange-500/40 text-orange-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>
                      {tf}:{p === 'ABOVE' ? '↑' : p === 'INSIDE' ? '○' : '↓'}
                    </button>
                  )
                })
              })}
              <span className="text-gray-400">str :</span>
              {(['1h', '4h'] as const).map(tf => {
                const val = tf === '1h' ? obStrength1h : obStrength4h
                const setter = tf === '1h' ? setObStrength1h : setObStrength4h
                return ['STRONG','MEDIUM','WEAK'].map(s => {
                  const active = val.includes(s)
                  return (
                    <button key={`obs-${tf}-${s}`} onClick={() => setter(active ? val.filter(x => x !== s) : [...val, s])}
                      className={cn("px-1.5 py-0.5 rounded border", active ? 'bg-orange-500/20 border-orange-500/40 text-orange-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>
                      {tf}:{s[0]}
                    </button>
                  )
                })
              })}
              <span className="text-gray-400">mit :</span>
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'obm1-'+o} onClick={() => setObMitig1h(o)} className={cn("px-1.5 py-0.5 rounded border", obMitig1h === o ? 'bg-orange-500/20 border-orange-500/40 text-orange-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>1H:{o.toLowerCase()}</button>
              ))}
              {(['ALL','YES','NO'] as const).map(o => (
                <button key={'obm4-'+o} onClick={() => setObMitig4h(o)} className={cn("px-1.5 py-0.5 rounded border", obMitig4h === o ? 'bg-orange-500/20 border-orange-500/40 text-orange-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>4H:{o.toLowerCase()}</button>
              ))}
            </div>

            {/* FVG position */}
            <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
              <span className="text-gray-400">🌫 FVG pos :</span>
              {(['1h', '4h'] as const).map(tf => {
                const val = tf === '1h' ? fvgPos1h : fvgPos4h
                const setter = tf === '1h' ? setFvgPos1h : setFvgPos4h
                return ['ABOVE','INSIDE','BELOW'].map(p => {
                  const active = val.includes(p)
                  return (
                    <button key={`fvg-${tf}-${p}`} onClick={() => setter(active ? val.filter(x => x !== p) : [...val, p])}
                      className={cn("px-1.5 py-0.5 rounded border", active ? 'bg-pink-500/20 border-pink-500/40 text-pink-300' : 'bg-gray-800 border-gray-700 text-gray-500')}>
                      {tf}:{p === 'ABOVE' ? '↑' : p === 'INSIDE' ? '○' : '↓'}
                    </button>
                  )
                })
              })}
            </div>
          </div>

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
              <button onClick={() => {
                setDecisionFilter('ALL'); setOutcomeFilter('ALL'); setVipFilter('ALL');
                setMinDiPlus('37'); setMaxDiPlus('50');
                setMinDiMinus('0'); setMaxDiMinus('14');
                setMinAdx('15'); setMaxAdx('100');
                setMinRsi('0'); setMaxRsi('79');
                setMinPuissance('0'); setMinVolPct('0');
                setMinChange24h(''); setMaxChange24h('36');
                setMinBody4h('2.7'); setMaxBody4h('100');
                setMinRange4h('0'); setMaxRange4h('34');
                setMinDiSpread('0'); setMaxDiSpread('45');
                setMinAdxDim('3'); setMaxAdxDim('');
                setMinVol1h('-100'); setMinVol4h('-100'); setMinVol24h('-100'); setMinVol48h('-100');
                setMaxVol1h(''); setMaxVol4h(''); setMaxVol24h(''); setMaxVol48h('');
                setMinTfBody('0');
                setMinStc15m('0.1'); setMaxStc15m('');
                setMinStc30m('0.2'); setMaxStc30m('');
                setMinStc1h('0.1'); setMaxStc1h('');
                setDirFilter('green');
                setFgFilter([]); setBtcTrendFilter('ALL'); setEthTrendFilter('ALL'); setAltSeasonFilter('ALL');
                setPpFilter('YES'); setEcFilter('YES');
                setTfFilter(['15m']);
                setCondFilters([]);
                setExcludeAllRedVol(true);
                setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-pink-500/10 border-pink-500/30 text-pink-400 hover:bg-pink-500/20"
              title="Custom: Range≤34, DI-≤14, RSI≤79, STC mins, green 15m, PP+EC, vol tout rouge exclu"
              >Custom</button>
              <button onClick={() => {
                setDecisionFilter('ALL'); setOutcomeFilter('ALL'); setVipFilter('ALL');
                setMinScore('8');
                setMinDiPlus('0'); setMaxDiPlus('100');
                setMinDiMinus('0'); setMaxDiMinus('25');
                setMinAdx('0'); setMaxAdx('100');
                setMinRsi('0'); setMaxRsi('80');
                setMinPuissance('0'); setMinVolPct('0');
                setMinChange24h(''); setMaxChange24h('100');
                setMinBody4h('2'); setMaxBody4h('100');
                setMinRange4h('0'); setMaxRange4h('34');
                setMinDiSpread('0'); setMaxDiSpread('80');
                setMinVol1h(''); setMinVol4h(''); setMinVol24h('100'); setMinVol48h('');
                setMaxVol1h(''); setMaxVol4h(''); setMaxVol24h('2000'); setMaxVol48h('');
                setMinTfBody('0');
                setMinStc15m('0.1'); setMaxStc15m('');
                setMinStc30m('0.2'); setMaxStc30m('');
                setMinStc1h('0.1'); setMaxStc1h('');
                setDirFilter('green');
                setFgFilter([]); setBtcTrendFilter('ALL'); setEthTrendFilter('ALL'); setAltSeasonFilter('ALL');
                setPpFilter('YES'); setEcFilter('YES');
                setTfFilter(['15m']);
                setCondFilters([]);
                setV8v9AllMode(false); setShowAdvanced(true);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-fuchsia-500/10 border-fuchsia-500/30 text-fuchsia-400 hover:bg-fuchsia-500/20"
              title="Custom Pro: Score≥8, RSI≤80, V24h 100-2000%, Range≤34, Body≥2, DI-≤25, green 15m, PP+EC"
              >Custom Pro</button>
              <button onClick={() => {
                setDecisionFilter('ALL'); setOutcomeFilter('ALL'); setVipFilter('ALL');
                setDirFilter('ALL'); setPpFilter('ALL'); setEcFilter('ALL');
                setBtcTrendFilter('ALL'); setEthTrendFilter('ALL');
                setMinBody4h(''); setMaxBody4h(''); setMinRange4h(''); setMaxRange4h('');
                setMinAdx(''); setMaxAdx(''); setMinDiSpread(''); setMaxDiSpread('');
                setMinDiPlus(''); setMaxDiPlus(''); setMinDiMinus(''); setMaxDiMinus('');
                setMinRsi(''); setMaxRsi(''); setMinChange24h(''); setMaxChange24h('');
                setMinVol1h(''); setMinVol4h(''); setMinVol24h(''); setMinVol48h('');
                setMaxVol1h(''); setMaxVol4h(''); setMaxVol24h(''); setMaxVol48h('');
                setExcludeAllRedVol(false); setExcludeGrayIndicators(false);
                setMinAdxDim(''); setMaxAdxDim('');
                setMaxStc15m(''); setMaxStc30m(''); setMaxStc1h(''); setMinTfBody('');
                setMinStc15m(''); setMinStc30m(''); setMinStc1h('');
                setV8v9AllMode(false);
              }} className="px-2 py-1 rounded text-[10px] font-medium border transition-colors bg-gray-700/40 border-gray-600 text-gray-300 hover:bg-gray-600/60"
              title="Réinitialiser tous les filtres (garde recherche pair + dates)"
              >↺ Reset</button>
            </div>
          </div>

          {/* View presets + Column Picker */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] text-gray-500 uppercase">Vue :</span>
            <button onClick={() => setVisibleCols(new Set(VIEW_CLASSIC))}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                setsEqual(visibleCols, VIEW_CLASSIC)
                  ? "bg-blue-500/20 border-blue-500/40 text-blue-300"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700")}>
              📋 Classique
            </button>
            <button onClick={() => setVisibleCols(new Set(VIEW_OPENCLAW))}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                setsEqual(visibleCols, VIEW_OPENCLAW)
                  ? "bg-fuchsia-500/20 border-fuchsia-500/40 text-fuchsia-300"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700")}>
              🔬 Analyse OpenClaw
            </button>
            <button onClick={() => setVisibleCols(new Set(ALL_COLUMNS.map(c => c.key)))}
              className={cn("px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
                visibleCols.size === ALL_COLUMNS.length
                  ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700")}>
              🌐 Tout
            </button>
            <span className="text-gray-600">|</span>
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
                    {col('adx_minus_dim') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" onClick={() => toggleSort('adx_minus_dim')} title="ADX - DI-">A−D−{sortIcon('adx_minus_dim')}</th>}
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
                    {col('prog') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Conditions progressives effectives (avec tolérance -2%) /5" onClick={() => toggleSort('prog')}>Prog{sortIcon('prog')}</th>}
                    {col('bonus_n') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Bonus filters validés /23" onClick={() => toggleSort('bonus_n')}>Bonus{sortIcon('bonus_n')}</th>}
                    {col('fib4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Fibonacci 4H bonus" onClick={() => toggleSort('fib4h')}>Fib4{sortIcon('fib4h')}</th>}
                    {col('fib1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Fibonacci 1H bonus" onClick={() => toggleSort('fib1h')}>Fib1{sortIcon('fib1h')}</th>}
                    {col('vp4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Volume Profile 4H position" onClick={() => toggleSort('vp4h')}>VP4{sortIcon('vp4h')}</th>}
                    {col('vp1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Volume Profile 1H position" onClick={() => toggleSort('vp1h')}>VP1{sortIcon('vp1h')}</th>}
                    {col('ob4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Order Block 4H position+strength" onClick={() => toggleSort('ob4h')}>OB4{sortIcon('ob4h')}</th>}
                    {col('ob1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Order Block 1H position+strength" onClick={() => toggleSort('ob1h')}>OB1{sortIcon('ob1h')}</th>}
                    {col('macd4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="MACD 4H trend" onClick={() => toggleSort('macd4h')}>MACD4{sortIcon('macd4h')}</th>}
                    {col('macd1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="MACD 1H trend" onClick={() => toggleSort('macd1h')}>MACD1{sortIcon('macd1h')}</th>}
                    {col('stoch4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="StochRSI 4H zone" onClick={() => toggleSort('stoch4h')}>Sto4{sortIcon('stoch4h')}</th>}
                    {col('stoch1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="StochRSI 1H zone" onClick={() => toggleSort('stoch1h')}>Sto1{sortIcon('stoch1h')}</th>}
                    {col('ema_st4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="EMA Stack 4H count /4" onClick={() => toggleSort('ema_st4h')}>EMS4{sortIcon('ema_st4h')}</th>}
                    {col('ema_st1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="EMA Stack 1H count /4" onClick={() => toggleSort('ema_st1h')}>EMS1{sortIcon('ema_st1h')}</th>}
                    {col('bb4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Bollinger Squeeze 4H" onClick={() => toggleSort('bb4h')}>BB4{sortIcon('bb4h')}</th>}
                    {col('fvg4h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="Fair Value Gap 4H position" onClick={() => toggleSort('fvg4h')}>FVG4{sortIcon('fvg4h')}</th>}
                    {col('adx1h') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="ADX 1H" onClick={() => toggleSort('adx1h')}>ADX1{sortIcon('adx1h')}</th>}
                    {col('rsi_mtf') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="RSI MTF aligned count /3" onClick={() => toggleSort('rsi_mtf')}>RsiMtf{sortIcon('rsi_mtf')}</th>}
                    {col('ml') && <th className="px-1 py-2 text-center text-[10px] cursor-pointer hover:text-gray-200" title="ML p_success" onClick={() => toggleSort('ml')}>ML{sortIcon('ml')}</th>}
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
                            {col('adx_minus_dim') && <td className="px-1 py-1 text-center">{adx != null && diMinus != null ? (() => { const ad = adx - diMinus; const c3 = ad >= 30 ? 'text-green-400' : ad >= 15 ? 'text-yellow-400' : ad < 0 ? 'text-red-400' : 'text-gray-400'; return <span className={cn("text-[10px] font-mono", c3)} title={`ADX ${adx.toFixed(0)} - DI- ${diMinus.toFixed(0)}`}>{ad >= 0 ? '+' : ''}{ad.toFixed(0)}</span> })() : dash}</td>}
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
                            {/* ─── Tier 3 cells ─── */}
                            {col('prog') && <td className="px-1 py-1 text-center text-[10px]">{fp.prog_count_effective != null ? <span className={cn('font-bold', fp.prog_count_effective >= 4 ? 'text-green-400' : fp.prog_count_effective >= 3 ? 'text-yellow-400' : 'text-red-400')}>{fp.prog_count_effective}/5</span> : dash}</td>}
                            {col('bonus_n') && <td className="px-1 py-1 text-center text-[10px]">{fp.bonus_count != null ? <span className={cn('font-mono', fp.bonus_count >= 12 ? 'text-green-400' : fp.bonus_count >= 8 ? 'text-yellow-400' : 'text-gray-400')}>{fp.bonus_count}</span> : dash}</td>}
                            {col('fib4h') && <td className="px-1 py-1 text-center text-[10px]">{fp.fib_4h_bonus === true ? <span className="text-yellow-400">✓</span> : fp.fib_4h_bonus === false ? <span className="text-gray-600">✗</span> : dash}</td>}
                            {col('fib1h') && <td className="px-1 py-1 text-center text-[10px]">{fp.fib_1h_bonus === true ? <span className="text-yellow-400">✓</span> : fp.fib_1h_bonus === false ? <span className="text-gray-600">✗</span> : dash}</td>}
                            {col('vp4h') && <td className="px-1 py-1 text-center text-[9px]">{fp.vp_4h_position ? <span className={cn('px-1 rounded', fp.vp_4h_position === 'IN_VA' ? 'bg-purple-500/20 text-purple-300' : fp.vp_4h_position === 'ABOVE_VAH' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300')}>{fp.vp_4h_position === 'IN_VA' ? 'IN' : fp.vp_4h_position === 'ABOVE_VAH' ? '↑' : '↓'}</span> : dash}</td>}
                            {col('vp1h') && <td className="px-1 py-1 text-center text-[9px]">{fp.vp_1h_position ? <span className={cn('px-1 rounded', fp.vp_1h_position === 'IN_VA' ? 'bg-purple-500/20 text-purple-300' : fp.vp_1h_position === 'ABOVE_VAH' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300')}>{fp.vp_1h_position === 'IN_VA' ? 'IN' : fp.vp_1h_position === 'ABOVE_VAH' ? '↑' : '↓'}</span> : dash}</td>}
                            {col('ob4h') && <td className="px-1 py-1 text-center text-[9px]">{fp.ob_4h_position ? <span className={cn('px-1 rounded', fp.ob_4h_strength === 'STRONG' ? 'bg-orange-500/20 text-orange-300' : 'bg-gray-700/40 text-gray-300')}>{fp.ob_4h_position === 'INSIDE' ? '○' : fp.ob_4h_position === 'ABOVE' ? '↑' : '↓'}{fp.ob_4h_strength?.[0] ?? ''}</span> : dash}</td>}
                            {col('ob1h') && <td className="px-1 py-1 text-center text-[9px]">{fp.ob_1h_position ? <span className={cn('px-1 rounded', fp.ob_1h_strength === 'STRONG' ? 'bg-orange-500/20 text-orange-300' : 'bg-gray-700/40 text-gray-300')}>{fp.ob_1h_position === 'INSIDE' ? '○' : fp.ob_1h_position === 'ABOVE' ? '↑' : '↓'}{fp.ob_1h_strength?.[0] ?? ''}</span> : dash}</td>}
                            {col('macd4h') && <td className="px-1 py-1 text-center text-[10px]">{fp.macd_4h_trend ? <span className={cn(fp.macd_4h_trend === 'BULLISH' ? 'text-green-400' : 'text-red-400')}>{fp.macd_4h_trend === 'BULLISH' ? '🟢' : '🔴'}{fp.macd_4h_growing ? '↑' : ''}</span> : dash}</td>}
                            {col('macd1h') && <td className="px-1 py-1 text-center text-[10px]">{fp.macd_1h_trend ? <span className={cn(fp.macd_1h_trend === 'BULLISH' ? 'text-green-400' : 'text-red-400')}>{fp.macd_1h_trend === 'BULLISH' ? '🟢' : '🔴'}{fp.macd_1h_growing ? '↑' : ''}</span> : dash}</td>}
                            {col('stoch4h') && <td className="px-1 py-1 text-center text-[9px]">{fp.stochrsi_4h_zone ? <span className={cn('px-1 rounded', fp.stochrsi_4h_zone === 'OVERSOLD' ? 'bg-emerald-500/20 text-emerald-300' : fp.stochrsi_4h_zone === 'OVERBOUGHT' ? 'bg-red-500/20 text-red-300' : 'bg-gray-700/40 text-gray-300')}>{fp.stochrsi_4h_zone === 'OVERSOLD' ? 'OS' : fp.stochrsi_4h_zone === 'OVERBOUGHT' ? 'OB' : 'N'}{fp.stochrsi_4h_k != null ? <span className="text-[8px] text-gray-500 ml-0.5">{Math.round(fp.stochrsi_4h_k)}</span> : ''}</span> : dash}</td>}
                            {col('stoch1h') && <td className="px-1 py-1 text-center text-[9px]">{fp.stochrsi_1h_zone ? <span className={cn('px-1 rounded', fp.stochrsi_1h_zone === 'OVERSOLD' ? 'bg-emerald-500/20 text-emerald-300' : fp.stochrsi_1h_zone === 'OVERBOUGHT' ? 'bg-red-500/20 text-red-300' : 'bg-gray-700/40 text-gray-300')}>{fp.stochrsi_1h_zone === 'OVERSOLD' ? 'OS' : fp.stochrsi_1h_zone === 'OVERBOUGHT' ? 'OB' : 'N'}{fp.stochrsi_1h_k != null ? <span className="text-[8px] text-gray-500 ml-0.5">{Math.round(fp.stochrsi_1h_k)}</span> : ''}</span> : dash}</td>}
                            {col('ema_st4h') && <td className="px-1 py-1 text-center text-[10px]">{fp.ema_stack_4h_count != null ? <span className={cn('font-mono', fp.ema_stack_4h_count >= 4 ? 'text-green-400 font-bold' : fp.ema_stack_4h_count >= 2 ? 'text-yellow-400' : 'text-gray-500')}>{fp.ema_stack_4h_count}/4</span> : dash}</td>}
                            {col('ema_st1h') && <td className="px-1 py-1 text-center text-[10px]">{fp.ema_stack_1h_count != null ? <span className={cn('font-mono', fp.ema_stack_1h_count >= 4 ? 'text-green-400 font-bold' : fp.ema_stack_1h_count >= 2 ? 'text-yellow-400' : 'text-gray-500')}>{fp.ema_stack_1h_count}/4</span> : dash}</td>}
                            {col('bb4h') && <td className="px-1 py-1 text-center text-[10px]">{fp.bb_4h_squeeze === true ? <span className="text-cyan-400">⚡</span> : fp.bb_4h_squeeze === false ? <span className="text-gray-600">·</span> : dash}</td>}
                            {col('fvg4h') && <td className="px-1 py-1 text-center text-[9px]">{fp.fvg_4h_position ? <span className={cn('px-1 rounded', fp.fvg_4h_position === 'INSIDE' ? 'bg-pink-500/20 text-pink-300' : fp.fvg_4h_position === 'ABOVE' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300')}>{fp.fvg_4h_position === 'INSIDE' ? '○' : fp.fvg_4h_position === 'ABOVE' ? '↑' : '↓'}</span> : dash}</td>}
                            {col('adx1h') && <td className="px-1 py-1 text-center text-[10px]">{fp.adx_1h != null ? <span className={cn('font-mono', fp.adx_1h >= 25 ? 'text-green-400' : fp.adx_1h >= 20 ? 'text-yellow-400' : 'text-red-400')}>{Math.round(fp.adx_1h)}</span> : dash}</td>}
                            {col('rsi_mtf') && <td className="px-1 py-1 text-center text-[10px]">{fp.rsi_mtf_aligned_count != null ? <span className={cn('font-mono', fp.rsi_mtf_aligned_count === 3 ? 'text-green-400 font-bold' : fp.rsi_mtf_aligned_count >= 2 ? 'text-yellow-400' : 'text-gray-500')}>{fp.rsi_mtf_aligned_count}/3</span> : dash}</td>}
                            {col('ml') && <td className="px-1 py-1 text-center text-[10px]">{fp.ml_p_success != null ? <span className={cn('font-mono', fp.ml_p_success >= 0.7 ? 'text-green-400 font-bold' : fp.ml_p_success >= 0.55 ? 'text-yellow-400' : 'text-red-400')}>{Math.round(fp.ml_p_success * 100)}%</span> : dash}</td>}
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
