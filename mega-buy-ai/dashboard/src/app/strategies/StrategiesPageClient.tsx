'use client'

import { useState, useEffect, useMemo } from 'react'
import { Target, TrendingUp, Shield, Zap, CheckCircle, XCircle, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, RefreshCw } from 'lucide-react'
import { AdvancedFilters } from '@/components/AdvancedFilters'
import { FilteredStats } from '@/components/FilteredStats'
import { useAdvancedFilters } from '@/hooks/useAdvancedFilters'
import { filterAlerts } from '@/lib/filterAlerts'

interface Strategy {
  id: string
  name: string
  description: string
  expected_precision: string
  expected_trades: string
  color: string
  thresholds: { trade: number; watch: number }
}

interface StrategyStats {
  trade: number
  watch: number
  skip: number
  tradeSuccess: number
  precision: number
}

interface AlertWithStrategy {
  id: string
  pair: string
  timeframes: string[]
  alert_timestamp: string
  bougie_4h: string
  score: number
  price: number
  rsi: number
  di_plus_4h: number
  di_minus_4h: number
  adx_4h: number
  vol_pct: number
  rsi_move: number
  rsi_check: boolean
  dmi_check: boolean
  ast_check: boolean
  choch: boolean
  zone: boolean
  lazy: boolean
  vol: boolean
  st: boolean
  pp: boolean
  ec: boolean
  // New metrics
  emotion: string
  puissance: number
  dmi_cross_4h: boolean
  range_4h: number
  body_4h: number
  lazy_4h: string
  lazy_values: Record<string, string>
  lazy_moves: Record<string, string>
  nb_timeframes: number
  ec_moves: Record<string, number>
  // ML & Outcomes
  p_success: number
  confidence: number
  decision: string
  max_profit_pct: number
  max_drawdown_pct: number
  is_success: boolean
  [key: string]: unknown
}

const ITEMS_PER_PAGE = 50
const CACHE_KEY = 'strategies_cache'
const CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

interface CachedData {
  strategies: Strategy[]
  stats: Record<string, StrategyStats>
  alerts: AlertWithStrategy[]
  timestamp: number
}

function getCache(): CachedData | null {
  if (typeof window === 'undefined') return null
  try {
    const cached = sessionStorage.getItem(CACHE_KEY)
    if (!cached) return null
    const data = JSON.parse(cached) as CachedData
    // Check if cache is still valid
    if (Date.now() - data.timestamp > CACHE_DURATION) {
      sessionStorage.removeItem(CACHE_KEY)
      return null
    }
    return data
  } catch {
    return null
  }
}

function setCache(data: CachedData) {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(data))
  } catch {
    // Ignore storage errors
  }
}

export default function StrategiesPageClient() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [stats, setStats] = useState<Record<string, StrategyStats>>({})
  const [currentStrategy, setCurrentStrategy] = useState('balanced')
  const [allAlerts, setAllAlerts] = useState<AlertWithStrategy[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingProgress, setLoadingProgress] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<string>('max_profit_pct')
  const [sortDesc, setSortDesc] = useState(true)

  // Advanced filters
  const { filters } = useAdvancedFilters()

  useEffect(() => {
    // Try to load from cache first
    const cached = getCache()
    if (cached) {
      setStrategies(cached.strategies)
      setStats(cached.stats)
      setAllAlerts(cached.alerts)
      setLoading(false)
    } else {
      loadStrategies(currentStrategy)
    }
  }, [])

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters])

  const loadStrategies = async (strategyId: string, forceRefresh = false) => {
    // Check cache unless forced refresh
    if (!forceRefresh) {
      const cached = getCache()
      if (cached) {
        setStrategies(cached.strategies)
        setStats(cached.stats)
        setAllAlerts(cached.alerts)
        setCurrentStrategy(strategyId)
        setLoading(false)
        return
      }
    }

    setLoading(true)
    setLoadingProgress('Chargement des stats...')

    try {
      // First load stats only (fast)
      const statsRes = await fetch(`/api/strategies?strategy=${strategyId}&statsOnly=true`)
      const statsData = await statsRes.json()

      setStrategies(statsData.strategies || [])
      setStats(statsData.stats || {})
      setCurrentStrategy(strategyId)

      const totalPages = statsData.pagination?.totalPages || 1
      const totalAlerts = statsData.pagination?.total || 0

      // Then load all alerts in batches
      setLoadingProgress(`Chargement des alertes (0/${totalAlerts})...`)
      const allData: AlertWithStrategy[] = []

      for (let page = 1; page <= totalPages; page++) {
        const res = await fetch(`/api/strategies?strategy=${strategyId}&page=${page}&limit=50`)
        const data = await res.json()
        allData.push(...(data.alerts || []))
        setLoadingProgress(`Chargement des alertes (${allData.length}/${totalAlerts})...`)
      }

      setAllAlerts(allData)
      setCurrentPage(1)

      // Save to cache
      setCache({
        strategies: statsData.strategies || [],
        stats: statsData.stats || {},
        alerts: allData,
        timestamp: Date.now()
      })
    } catch (error) {
      console.error('Error loading strategies:', error)
    }
    setLoading(false)
    setLoadingProgress('')
  }

  // Force refresh function
  const handleRefresh = () => {
    sessionStorage.removeItem(CACHE_KEY)
    loadStrategies(currentStrategy, true)
  }

  const getIcon = (strategyId: string) => {
    switch (strategyId) {
      case 'aggressive': return <Zap className="w-5 h-5" />
      case 'balanced': return <Target className="w-5 h-5" />
      case 'selective': return <TrendingUp className="w-5 h-5" />
      case 'conservative': return <Shield className="w-5 h-5" />
      default: return <Target className="w-5 h-5" />
    }
  }

  const getColorClasses = (color: string) => {
    const colors: Record<string, { bg: string; border: string; text: string; ring: string }> = {
      red: { bg: 'bg-red-500/10', border: 'border-red-500', text: 'text-red-400', ring: 'ring-red-500' },
      blue: { bg: 'bg-blue-500/10', border: 'border-blue-500', text: 'text-blue-400', ring: 'ring-blue-500' },
      green: { bg: 'bg-green-500/10', border: 'border-green-500', text: 'text-green-400', ring: 'ring-green-500' },
      purple: { bg: 'bg-purple-500/10', border: 'border-purple-500', text: 'text-purple-400', ring: 'ring-purple-500' }
    }
    return colors[color] || colors.blue
  }

  // Apply filters, then sort
  const filteredAlerts = useMemo(() => {
    // First apply advanced filters
    const filtered = filterAlerts(allAlerts, filters)

    // Then sort
    return filtered.sort((a, b) => {
      const aVal = (a as any)[sortBy]
      const bVal = (b as any)[sortBy]

      // Handle date/timestamp sorting
      if (sortBy === 'alert_timestamp' || sortBy === 'bougie_4h') {
        const aDate = aVal ? new Date(aVal).getTime() : 0
        const bDate = bVal ? new Date(bVal).getTime() : 0
        return sortDesc ? bDate - aDate : aDate - bDate
      }

      // Handle string sorting (pair, etc.)
      if (sortBy === 'pair') {
        const aStr = (aVal || '').toString()
        const bStr = (bVal || '').toString()
        return sortDesc ? bStr.localeCompare(aStr) : aStr.localeCompare(bStr)
      }

      // Numeric sorting (default)
      const aNum = aVal ?? 0
      const bNum = bVal ?? 0
      return sortDesc ? bNum - aNum : aNum - bNum
    })
  }, [allAlerts, filters, sortBy, sortDesc])

  // Client-side pagination on filtered results
  const totalPages = Math.ceil(filteredAlerts.length / ITEMS_PER_PAGE)
  const paginatedAlerts = filteredAlerts.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  )

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortDesc(!sortDesc)
    } else {
      setSortBy(column)
      setSortDesc(true)
    }
  }

  const SortHeader = ({ column, label }: { column: string; label: string }) => (
    <th
      className="py-2 px-2 text-gray-400 cursor-pointer hover:text-white transition-colors"
      onClick={() => handleSort(column)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortBy === column && (
          <span className="text-blue-400">{sortDesc ? '↓' : '↑'}</span>
        )}
      </div>
    </th>
  )

  const CheckIcon = ({ checked }: { checked: boolean }) => (
    checked ? <span className="text-green-400">✓</span> : <span className="text-gray-600">-</span>
  )

  const currentStats = stats[currentStrategy]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg">
            <Target className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Strategies de Trading</h1>
            <p className="text-gray-400 text-sm">
              {allAlerts.length > 0 ? `${allAlerts.length} alertes chargées` : 'Comparez et selectionnez la strategie adaptee a votre profil de risque'}
            </p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors disabled:opacity-50"
          title="Actualiser les données"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span className="text-sm">Actualiser</span>
        </button>
      </div>

      {/* Strategy Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {strategies.map(strategy => {
          const strategyStats = stats[strategy.id]
          const isSelected = currentStrategy === strategy.id
          const colors = getColorClasses(strategy.color)

          return (
            <button
              key={strategy.id}
              onClick={() => loadStrategies(strategy.id)}
              disabled={loading}
              className={`relative p-5 rounded-xl text-left transition-all duration-200 ${
                isSelected
                  ? `${colors.bg} border-2 ${colors.border} ring-2 ${colors.ring} ring-opacity-30`
                  : 'bg-gray-900 border border-gray-800 hover:border-gray-700'
              } ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
            >
              {isSelected && (
                <div className={`absolute top-2 right-2 px-2 py-0.5 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
                  Actif
                </div>
              )}

              <div className={`mb-3 ${isSelected ? colors.text : 'text-gray-400'}`}>
                {getIcon(strategy.id)}
              </div>

              <h3 className={`text-lg font-semibold mb-1 ${isSelected ? 'text-white' : 'text-gray-200'}`}>
                {strategy.name}
              </h3>

              <p className="text-xs text-gray-500 mb-4">{strategy.description}</p>

              {strategyStats && (
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">TRADE</span>
                    <span className="text-sm font-medium text-white">{strategyStats.trade}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">Precision</span>
                    <span className={`text-sm font-bold ${
                      strategyStats.precision >= 60 ? 'text-green-400' :
                      strategyStats.precision >= 40 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {strategyStats.precision.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">Succes</span>
                    <span className="text-sm text-gray-300">
                      {strategyStats.tradeSuccess}/{strategyStats.trade}
                    </span>
                  </div>

                  <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden mt-2">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        strategyStats.precision >= 60 ? 'bg-green-500' :
                        strategyStats.precision >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(strategyStats.precision, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Loading Progress */}
      {loading && loadingProgress && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-center">
          <p className="text-blue-400">{loadingProgress}</p>
        </div>
      )}

      {/* Advanced Filters - Always visible */}
      <AdvancedFilters resultCount={filteredAlerts.length} showDecisions={true} />

      {/* Filtered Performance Stats */}
      <FilteredStats alerts={filteredAlerts} showDecisions={true} />

      {/* Current Strategy Details */}
      {currentStats && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Resume: {strategies.find(s => s.id === currentStrategy)?.name}
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
              <p className="text-green-400 text-sm mb-1">TRADE</p>
              <p className="text-2xl font-bold text-green-400">{currentStats.trade}</p>
              <p className="text-xs text-gray-500">{currentStats.tradeSuccess} succes</p>
            </div>
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <p className="text-yellow-400 text-sm mb-1">WATCH</p>
              <p className="text-2xl font-bold text-yellow-400">{currentStats.watch}</p>
            </div>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <p className="text-red-400 text-sm mb-1">SKIP</p>
              <p className="text-2xl font-bold text-red-400">{currentStats.skip}</p>
            </div>
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
              <p className="text-blue-400 text-sm mb-1">Precision TRADE</p>
              <p className="text-2xl font-bold text-blue-400">{currentStats.precision.toFixed(1)}%</p>
            </div>
          </div>

          {/* Pagination Controls - Top */}
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-400">
              Affichage {filteredAlerts.length > 0 ? ((currentPage - 1) * ITEMS_PER_PAGE) + 1 : 0} - {Math.min(currentPage * ITEMS_PER_PAGE, filteredAlerts.length)} sur {filteredAlerts.length}
              {allAlerts.length !== filteredAlerts.length && ` (${allAlerts.length} total)`}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 py-1 text-sm text-white">
                Page {currentPage} / {totalPages || 1}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages || totalPages === 0}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages || totalPages === 0}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Alerts Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-800 text-left">
                  <th className="py-2 px-2 text-gray-400 text-center w-10">#</th>
                  <SortHeader column="alert_timestamp" label="Date/Heure" />
                  <SortHeader column="pair" label="Paire" />
                  <th className="py-2 px-2 text-gray-400">TF</th>
                  <SortHeader column="score" label="Score" />
                  <th className="py-2 px-2 text-gray-400">Emotion</th>
                  <SortHeader column="puissance" label="Puiss." />
                  <SortHeader column="p_success" label="P(ML)" />
                  <th className="py-2 px-2 text-gray-400">Decision</th>
                  <SortHeader column="rsi" label="RSI" />
                  <SortHeader column="di_plus_4h" label="DI+" />
                  <SortHeader column="di_minus_4h" label="DI-" />
                  <SortHeader column="adx_4h" label="ADX" />
                  <th className="py-2 px-2 text-gray-400 text-center" title="DMI Cross 4H">DMI✓</th>
                  <SortHeader column="range_4h" label="Rng%" />
                  <SortHeader column="body_4h" label="Body%" />
                  <SortHeader column="vol_pct" label="Vol%" />
                  <th className="py-2 px-2 text-purple-400 text-center" title="LazyBar 15m">LZ 15</th>
                  <th className="py-2 px-2 text-purple-400 text-center" title="LazyBar 30m">LZ 30</th>
                  <th className="py-2 px-2 text-purple-400 text-center" title="LazyBar 1h">LZ 1h</th>
                  <th className="py-2 px-2 text-purple-400 text-center" title="LazyBar 4h">LZ 4h</th>
                  <th className="py-2 px-2 text-cyan-400 text-center" title="EC RSI Move 15m">EC 15</th>
                  <th className="py-2 px-2 text-cyan-400 text-center" title="EC RSI Move 30m">EC 30</th>
                  <th className="py-2 px-2 text-cyan-400 text-center" title="EC RSI Move 1h">EC 1h</th>
                  <th className="py-2 px-2 text-cyan-400 text-center" title="EC RSI Move 4h">EC 4h</th>
                  <th className="py-2 px-2 text-gray-400 text-center" title="RSI/DMI/AST">Checks</th>
                  <th className="py-2 px-2 text-gray-400 text-center" title="ChoCH/Zone/Lazy/Vol/ST/PP/EC">Bonus</th>
                  <SortHeader column="max_profit_pct" label="Profit" />
                  <SortHeader column="max_drawdown_pct" label="DD" />
                  <th className="py-2 px-2 text-gray-400 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {paginatedAlerts.map((alert, index) => {
                  const rowNum = ((currentPage - 1) * ITEMS_PER_PAGE) + index + 1
                  const dateTime = alert.alert_timestamp ? new Date(alert.alert_timestamp) : null
                  const formattedDate = dateTime ? dateTime.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '-'
                  const formattedTime = dateTime ? dateTime.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : ''

                  return (
                  <tr key={alert.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 px-2 text-center text-gray-500">{rowNum}</td>
                    <td className="py-2 px-2 text-gray-400 whitespace-nowrap">
                      <div className="text-xs">{formattedDate}</div>
                      <div className="text-[10px] text-gray-500">{formattedTime}</div>
                    </td>
                    <td className="py-2 px-2 text-white font-medium">{alert.pair}</td>
                    <td className="py-2 px-2 text-gray-400 text-xs">
                      {alert.timeframes?.join(', ') || '-'}
                    </td>
                    <td className="py-2 px-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        (alert.score || 0) >= 9 ? 'bg-green-500/20 text-green-400' :
                        (alert.score || 0) >= 7 ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {alert.score || '-'}/10
                      </span>
                    </td>
                    <td className="py-2 px-2 text-xs whitespace-nowrap">
                      {alert.emotion || '-'}
                    </td>
                    <td className={`py-2 px-2 text-center ${
                      (alert.puissance || 0) >= 10 ? 'text-orange-400 font-bold' :
                      (alert.puissance || 0) >= 5 ? 'text-yellow-400' : 'text-gray-400'
                    }`}>
                      {alert.puissance || '-'}
                    </td>
                    <td className="py-2 px-2 text-gray-300">
                      {(alert.p_success * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 px-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        alert.decision === 'TRADE' ? 'bg-green-500/20 text-green-400' :
                        alert.decision === 'WATCH' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {alert.decision}
                      </span>
                    </td>
                    <td className={`py-2 px-2 ${
                      (alert.rsi || 0) >= 70 ? 'text-red-400' :
                      (alert.rsi || 0) >= 50 ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      {alert.rsi?.toFixed(1) || '-'}
                    </td>
                    <td className="py-2 px-2 text-green-400">{alert.di_plus_4h?.toFixed(1) || '-'}</td>
                    <td className="py-2 px-2 text-red-400">{alert.di_minus_4h?.toFixed(1) || '-'}</td>
                    <td className={`py-2 px-2 ${
                      (alert.adx_4h || 0) >= 25 ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      {alert.adx_4h?.toFixed(1) || '-'}
                    </td>
                    <td className="py-2 px-2 text-center">
                      {alert.dmi_cross_4h ? <span className="text-green-400">✓</span> : <span className="text-gray-600">✗</span>}
                    </td>
                    <td className={`py-2 px-2 ${
                      (alert.range_4h || 0) >= 3 ? 'text-orange-400' : 'text-gray-400'
                    }`}>
                      {alert.range_4h ? `${alert.range_4h.toFixed(1)}%` : '-'}
                    </td>
                    <td className={`py-2 px-2 ${
                      (alert.body_4h || 0) >= 2 ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      {alert.body_4h ? `${alert.body_4h.toFixed(1)}%` : '-'}
                    </td>
                    <td className={`py-2 px-2 ${
                      (alert.vol_pct || 0) >= 150 ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      {alert.vol_pct ? `${alert.vol_pct.toFixed(0)}%` : '-'}
                    </td>
                    {/* LazyBar per timeframe */}
                    {(['15m', '30m', '1h', '4h'] as const).map(tf => {
                      const lazyVals = alert.lazy_values || {}
                      let lzVal = lazyVals[tf]
                      // For 4h, fall back to lazy_4h field
                      if (tf === '4h' && (!lzVal || lzVal === '-') && alert.lazy_4h && alert.lazy_4h !== '-') {
                        lzVal = alert.lazy_4h
                      }
                      if (!lzVal || lzVal === '-') {
                        return <td key={`lz-${tf}`} className="py-2 px-2 text-center text-gray-600">-</td>
                      }
                      const numMatch = lzVal.match(/(\d+\.?\d*)/)
                      const numVal = numMatch ? parseFloat(numMatch[1]) : 0
                      const hasSpike = lzVal.includes('🔥')
                      const hasUp = lzVal.includes('⬆️')
                      return (
                        <td key={`lz-${tf}`} className="py-2 px-2 text-center">
                          <span className={`text-xs font-medium ${
                            lzVal.includes('Fuchsia') || lzVal.includes('Purple') ? 'text-fuchsia-400' :
                            lzVal.includes('Blue') || lzVal.includes('Navy') ? 'text-blue-400' :
                            lzVal.includes('Red') ? 'text-red-400' :
                            lzVal.includes('Orange') ? 'text-orange-400' :
                            lzVal.includes('Yellow') ? 'text-yellow-400' : 'text-cyan-400'
                          }`} title={lzVal}>
                            {hasSpike ? '🔥' : hasUp ? '⬆️' : ''}{numVal.toFixed(1)}
                          </span>
                        </td>
                      )
                    })}
                    {/* EC Moves per timeframe */}
                    {(['15m', '30m', '1h', '4h'] as const).map(tf => {
                      const ecMoves = alert.ec_moves || {}
                      const ecVal = ecMoves[tf]
                      if (ecVal === undefined || ecVal === null) {
                        return <td key={`ec-${tf}`} className="py-2 px-2 text-center text-gray-600">-</td>
                      }
                      // Thresholds: 🔥 >= 5, ⬆️ >= 3
                      const hasSpike = ecVal >= 5
                      const hasUp = ecVal >= 3 && ecVal < 5
                      return (
                        <td key={`ec-${tf}`} className="py-2 px-2 text-center">
                          <span className={`text-xs font-medium ${
                            hasSpike ? 'text-orange-400' :
                            hasUp ? 'text-cyan-400' : 'text-gray-400'
                          }`} title={`EC RSI Move: ${ecVal.toFixed(2)}`}>
                            {hasSpike ? '🔥' : hasUp ? '⬆️' : ''}{ecVal.toFixed(1)}
                          </span>
                        </td>
                      )
                    })}
                    <td className="py-2 px-2 text-center space-x-1">
                      <CheckIcon checked={alert.rsi_check} />
                      <CheckIcon checked={alert.dmi_check} />
                      <CheckIcon checked={alert.ast_check} />
                    </td>
                    <td className="py-2 px-2 text-center space-x-0.5">
                      <CheckIcon checked={alert.choch} />
                      <CheckIcon checked={alert.zone} />
                      <CheckIcon checked={alert.lazy} />
                      <CheckIcon checked={alert.vol} />
                      <CheckIcon checked={alert.st} />
                      <CheckIcon checked={alert.pp} />
                      <CheckIcon checked={alert.ec} />
                    </td>
                    <td className={`py-2 px-2 font-medium ${
                      (alert.max_profit_pct || 0) >= 5 ? 'text-green-400' :
                      (alert.max_profit_pct || 0) >= 0 ? 'text-gray-400' : 'text-red-400'
                    }`}>
                      {alert.max_profit_pct != null ? `${alert.max_profit_pct >= 0 ? '+' : ''}${alert.max_profit_pct.toFixed(2)}%` : '-'}
                    </td>
                    <td className={`py-2 px-2 ${
                      (alert.max_drawdown_pct || 0) > 10 ? 'text-red-400' :
                      (alert.max_drawdown_pct || 0) > 5 ? 'text-yellow-400' : 'text-gray-400'
                    }`}>
                      {alert.max_drawdown_pct != null ? `-${Math.abs(alert.max_drawdown_pct).toFixed(2)}%` : '-'}
                    </td>
                    <td className="py-2 px-2 text-center">
                      {alert.is_success ? (
                        <CheckCircle className="w-4 h-4 text-green-400 inline" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400 inline" />
                      )}
                    </td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls - Bottom */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-800">
            <div className="text-sm text-gray-400">
              {filteredAlerts.length === allAlerts.length
                ? `Total: ${filteredAlerts.length} alertes`
                : `Filtrées: ${filteredAlerts.length} / ${allAlerts.length} alertes`}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {/* Page numbers */}
              <div className="flex gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum
                  if (totalPages <= 5) {
                    pageNum = i + 1
                  } else if (currentPage <= 3) {
                    pageNum = i + 1
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i
                  } else {
                    pageNum = currentPage - 2 + i
                  }
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-2 py-1 rounded text-sm ${
                        currentPage === pageNum
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                      }`}
                    >
                      {pageNum}
                    </button>
                  )
                })}
              </div>

              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages || totalPages === 0}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages || totalPages === 0}
                className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
