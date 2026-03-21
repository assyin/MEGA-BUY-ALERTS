'use client'

import { useState } from 'react'
import { Filter, X, ChevronDown, ChevronUp, RotateCcw, Zap, Target, TrendingUp } from 'lucide-react'
import { useAdvancedFilters } from '@/hooks/useAdvancedFilters'
import {
  EMOTIONS,
  DECISIONS,
  TIMEFRAMES,
  CONDITIONS,
  AdvancedFilters as FiltersType
} from '@/types/filters'

// Preset filters for quick selection
const FILTER_PRESETS = {
  maxWinRate: {
    id: 'maxWinRate',
    name: 'Max Win Rate',
    description: '82% WR - Perd gros gagnants',
    icon: Zap,
    color: 'red',
    filters: {
      conditions: ['PP', 'EC'],
      minDiMinus: 22,
      maxDiPlus: 25,
      minAdx: 35,
      minVolPct: 100
    }
  },
  balanced: {
    id: 'balanced',
    name: 'Équilibré',
    description: '73% WR - Garde 67% gros gains',
    icon: Target,
    color: 'blue',
    filters: {
      conditions: ['PP', 'EC'],
      minDiMinus: 22,
      maxDiPlus: 20,
      minAdx: 21,
      minVolPct: 100
    }
  },
  keepBigWinners: {
    id: 'keepBigWinners',
    name: 'Gros Gagnants',
    description: '71% WR - Garde 92% gros gains',
    icon: TrendingUp,
    color: 'green',
    filters: {
      conditions: ['PP', 'EC'],
      minDiMinus: 22,
      maxDiPlus: 25,
      minAdx: 21,
      minVolPct: 100
    }
  }
}

interface AdvancedFiltersProps {
  resultCount?: number
  showDecisions?: boolean
}

export function AdvancedFilters({ resultCount, showDecisions = true }: AdvancedFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const {
    filters,
    setFilter,
    setFilters,
    resetFilters,
    toggleArrayFilter,
    activeCount,
    hasActiveFilters
  } = useAdvancedFilters()

  // Apply a preset filter
  const applyPreset = (presetId: string) => {
    const preset = FILTER_PRESETS[presetId as keyof typeof FILTER_PRESETS]
    if (!preset) return

    // Reset first, then apply preset filters
    setFilters(preset.filters as FiltersType)
    setActivePreset(presetId)
  }

  // Check if current filters match a preset
  const checkActivePreset = () => {
    for (const [id, preset] of Object.entries(FILTER_PRESETS)) {
      const pf = preset.filters
      if (
        filters.minDiMinus === pf.minDiMinus &&
        filters.maxDiPlus === pf.maxDiPlus &&
        filters.minAdx === pf.minAdx &&
        filters.minVolPct === pf.minVolPct &&
        filters.conditions?.includes('PP') &&
        filters.conditions?.includes('EC')
      ) {
        return id
      }
    }
    return null
  }

  const handleReset = () => {
    resetFilters()
    setActivePreset(null)
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header - Always visible */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-800/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <Filter className="w-5 h-5 text-blue-400" />
          <span className="font-medium text-white">Filtres Avancés</span>
          {activeCount > 0 && (
            <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full font-medium">
              {activeCount} actif{activeCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {resultCount !== undefined && (
            <span className="text-sm text-gray-400">
              {resultCount} résultat{resultCount !== 1 ? 's' : ''}
            </span>
          )}
          {hasActiveFilters && (
            <button
              onClick={(e) => { e.stopPropagation(); resetFilters(); }}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
              title="Réinitialiser les filtres"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* Preset Filter Buttons - Always visible */}
      <div className="px-4 py-3 border-t border-gray-800 bg-gray-850">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Préréglages Rapides</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.values(FILTER_PRESETS).map((preset) => {
            const Icon = preset.icon
            const isActive = activePreset === preset.id
            const colorClasses = {
              red: isActive
                ? 'bg-red-500 text-white border-red-500 shadow-lg shadow-red-500/25'
                : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20 hover:border-red-500/50',
              blue: isActive
                ? 'bg-blue-500 text-white border-blue-500 shadow-lg shadow-blue-500/25'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/30 hover:bg-blue-500/20 hover:border-blue-500/50',
              green: isActive
                ? 'bg-green-500 text-white border-green-500 shadow-lg shadow-green-500/25'
                : 'bg-green-500/10 text-green-400 border-green-500/30 hover:bg-green-500/20 hover:border-green-500/50'
            }
            return (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200 ${colorClasses[preset.color as keyof typeof colorClasses]}`}
              >
                <Icon className="w-4 h-4" />
                <div className="text-left">
                  <div className="text-sm font-medium">{preset.name}</div>
                  <div className={`text-xs ${isActive ? 'text-white/80' : 'opacity-70'}`}>{preset.description}</div>
                </div>
              </button>
            )
          })}
          {activePreset && (
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-600 bg-gray-700/50 text-gray-300 hover:bg-gray-600 hover:text-white transition-all"
            >
              <RotateCcw className="w-4 h-4" />
              <span className="text-sm">Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Content - Collapsible */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-800">
          {/* Row 1: Date Range, Pair, Score */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4">
            {/* Date Start */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date début</label>
              <input
                type="date"
                value={filters.dateStart || ''}
                onChange={(e) => setFilter('dateStart', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Date End */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date fin</label>
              <input
                type="date"
                value={filters.dateEnd || ''}
                onChange={(e) => setFilter('dateEnd', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Pair Search */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Paire</label>
              <input
                type="text"
                placeholder="BTC, ETH..."
                value={filters.pair || ''}
                onChange={(e) => setFilter('pair', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Score Range */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Score (min-max)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="10"
                  placeholder="0"
                  value={filters.minScore ?? ''}
                  onChange={(e) => setFilter('minScore', e.target.value ? parseInt(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  min="0"
                  max="10"
                  placeholder="10"
                  value={filters.maxScore ?? ''}
                  onChange={(e) => setFilter('maxScore', e.target.value ? parseInt(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Row 2: Emotion, Decision, Puissance */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Emotion */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Émotion</label>
              <div className="flex flex-wrap gap-1">
                {EMOTIONS.map(em => (
                  <button
                    key={em}
                    onClick={() => toggleArrayFilter('emotions', em)}
                    className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                      filters.emotions?.includes(em)
                        ? 'bg-purple-500 text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {em}
                  </button>
                ))}
              </div>
            </div>

            {/* Decision */}
            {showDecisions && (
              <div>
                <label className="block text-xs text-gray-500 mb-1">Decision</label>
                <div className="flex flex-wrap gap-1">
                  {DECISIONS.map(dec => (
                    <button
                      key={dec}
                      onClick={() => toggleArrayFilter('decisions', dec)}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        filters.decisions?.includes(dec)
                          ? dec === 'TRADE' ? 'bg-green-500 text-white' :
                            dec === 'WATCH' ? 'bg-yellow-500 text-black' :
                            'bg-red-500 text-white'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                      }`}
                    >
                      {dec}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Puissance */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Puissance ≥</label>
              <input
                type="number"
                min="0"
                placeholder="0"
                value={filters.minPuissance ?? ''}
                onChange={(e) => setFilter('minPuissance', e.target.value ? parseInt(e.target.value) : undefined)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* DMI Cross 4H */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">DMI Cross 4H</label>
              <select
                value={filters.dmiCross4h === true ? 'true' : filters.dmiCross4h === false ? 'false' : ''}
                onChange={(e) => {
                  const v = e.target.value
                  setFilter('dmiCross4h', v === 'true' ? true : v === 'false' ? false : undefined)
                }}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="">Tous</option>
                <option value="true">Oui ✓</option>
                <option value="false">Non ✗</option>
              </select>
            </div>
          </div>

          {/* Row 3: Timeframes */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Timeframes</label>
            <div className="flex flex-wrap gap-2">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => toggleArrayFilter('timeframes', tf)}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    filters.timeframes?.includes(tf)
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Row 4: Conditions */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Conditions (toutes requises)</label>
            <div className="flex flex-wrap gap-2">
              {CONDITIONS.map(cond => (
                <button
                  key={cond}
                  onClick={() => toggleArrayFilter('conditions', cond)}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                    filters.conditions?.includes(cond)
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {cond}
                </button>
              ))}
            </div>
          </div>

          {/* Row 5: LazyBar, EC, Vol%, Profit % */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* LazyBar Min */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">LazyBar ≥</label>
              <input
                type="number"
                min="0"
                step="0.1"
                placeholder="ex: 11"
                value={filters.minLazyBar ?? ''}
                onChange={(e) => setFilter('minLazyBar', e.target.value ? parseFloat(e.target.value) : undefined)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* EC Move Min */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">EC Move ≥</label>
              <input
                type="number"
                min="0"
                step="0.1"
                placeholder="ex: 3"
                value={filters.minEcMove ?? ''}
                onChange={(e) => setFilter('minEcMove', e.target.value ? parseFloat(e.target.value) : undefined)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Vol % Range */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-cyan-400">Vol % (min-max)</label>
                {filters.minVolPct !== undefined && (
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                    filters.minVolPct >= 200 ? 'bg-purple-500/20 text-purple-400' :
                    filters.minVolPct >= 150 ? 'bg-green-500/20 text-green-400' :
                    filters.minVolPct >= 100 ? 'bg-cyan-500/20 text-cyan-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {filters.minVolPct >= 200 ? 'Explosif' :
                     filters.minVolPct >= 150 ? 'Fort' :
                     filters.minVolPct >= 100 ? 'Normal' :
                     'Faible'}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  step="10"
                  placeholder="100"
                  value={filters.minVolPct ?? ''}
                  onChange={(e) => setFilter('minVolPct', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-cyan-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  min="0"
                  step="10"
                  placeholder="∞"
                  value={filters.maxVolPct ?? ''}
                  onChange={(e) => setFilter('maxVolPct', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-cyan-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Profit % Range */}
            <div>
              <label className="block text-xs text-emerald-400 mb-1">Profit % (min-max)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  step="0.1"
                  placeholder="min"
                  value={filters.minProfit ?? ''}
                  onChange={(e) => setFilter('minProfit', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-emerald-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  step="0.1"
                  placeholder="max"
                  value={filters.maxProfit ?? ''}
                  onChange={(e) => setFilter('maxProfit', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-emerald-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Row 6: RSI, DI+, DI-, ADX */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* RSI Range */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">RSI (min-max)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="0"
                  value={filters.minRsi ?? ''}
                  onChange={(e) => setFilter('minRsi', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="100"
                  value={filters.maxRsi ?? ''}
                  onChange={(e) => setFilter('maxRsi', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>

            {/* DI+ Range */}
            <div>
              <label className="block text-xs text-green-400 mb-1">DI+ (min-max)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="0"
                  value={filters.minDiPlus ?? ''}
                  onChange={(e) => setFilter('minDiPlus', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-green-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-green-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="100"
                  value={filters.maxDiPlus ?? ''}
                  onChange={(e) => setFilter('maxDiPlus', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-green-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-green-500 focus:outline-none"
                />
              </div>
            </div>

            {/* DI- Range */}
            <div>
              <label className="block text-xs text-red-400 mb-1">DI- (min-max)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="0"
                  value={filters.minDiMinus ?? ''}
                  onChange={(e) => setFilter('minDiMinus', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-red-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-red-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="100"
                  value={filters.maxDiMinus ?? ''}
                  onChange={(e) => setFilter('maxDiMinus', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-red-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-red-500 focus:outline-none"
                />
              </div>
            </div>

            {/* ADX Range */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-amber-400">ADX (min-max)</label>
                {filters.minAdx !== undefined && (
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                    filters.minAdx >= 50 ? 'bg-purple-500/20 text-purple-400' :
                    filters.minAdx >= 40 ? 'bg-green-500/20 text-green-400' :
                    filters.minAdx >= 20 ? 'bg-amber-500/20 text-amber-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {filters.minAdx >= 50 ? 'Très forte' :
                     filters.minAdx >= 40 ? 'Forte' :
                     filters.minAdx >= 20 ? 'Modéré' :
                     'Faible'}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="0"
                  value={filters.minAdx ?? ''}
                  onChange={(e) => setFilter('minAdx', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-amber-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-amber-500 focus:outline-none"
                />
                <span className="text-gray-500 self-center">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="100"
                  value={filters.maxAdx ?? ''}
                  onChange={(e) => setFilter('maxAdx', e.target.value ? parseFloat(e.target.value) : undefined)}
                  className="w-full px-3 py-2 bg-gray-800 border border-amber-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:border-amber-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Active Filters Summary */}
          {hasActiveFilters && (
            <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-800">
              {filters.dateStart && (
                <FilterBadge
                  label={`Depuis: ${filters.dateStart}`}
                  onRemove={() => setFilter('dateStart', undefined)}
                />
              )}
              {filters.dateEnd && (
                <FilterBadge
                  label={`Jusqu'à: ${filters.dateEnd}`}
                  onRemove={() => setFilter('dateEnd', undefined)}
                />
              )}
              {filters.pair && (
                <FilterBadge
                  label={`Paire: ${filters.pair}`}
                  onRemove={() => setFilter('pair', undefined)}
                />
              )}
              {filters.minScore !== undefined && (
                <FilterBadge
                  label={`Score ≥ ${filters.minScore}`}
                  onRemove={() => setFilter('minScore', undefined)}
                />
              )}
              {filters.maxScore !== undefined && (
                <FilterBadge
                  label={`Score ≤ ${filters.maxScore}`}
                  onRemove={() => setFilter('maxScore', undefined)}
                />
              )}
              {filters.minPuissance !== undefined && (
                <FilterBadge
                  label={`Puissance ≥ ${filters.minPuissance}`}
                  onRemove={() => setFilter('minPuissance', undefined)}
                />
              )}
              {filters.emotions?.map(em => (
                <FilterBadge
                  key={em}
                  label={em}
                  onRemove={() => toggleArrayFilter('emotions', em)}
                  className="bg-purple-500/20 text-purple-400"
                />
              ))}
              {filters.decisions?.map(dec => (
                <FilterBadge
                  key={dec}
                  label={dec}
                  onRemove={() => toggleArrayFilter('decisions', dec)}
                  className={
                    dec === 'TRADE' ? 'bg-green-500/20 text-green-400' :
                    dec === 'WATCH' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }
                />
              ))}
              {filters.timeframes?.map(tf => (
                <FilterBadge
                  key={tf}
                  label={tf}
                  onRemove={() => toggleArrayFilter('timeframes', tf)}
                  className="bg-blue-500/20 text-blue-400"
                />
              ))}
              {filters.conditions?.map(cond => (
                <FilterBadge
                  key={cond}
                  label={cond}
                  onRemove={() => toggleArrayFilter('conditions', cond)}
                  className="bg-green-500/20 text-green-400"
                />
              ))}
              {filters.dmiCross4h !== undefined && filters.dmiCross4h !== null && (
                <FilterBadge
                  label={`DMI Cross: ${filters.dmiCross4h ? 'Oui' : 'Non'}`}
                  onRemove={() => setFilter('dmiCross4h', undefined)}
                />
              )}
              {filters.minLazyBar !== undefined && (
                <FilterBadge
                  label={`LZ ≥ ${filters.minLazyBar}`}
                  onRemove={() => setFilter('minLazyBar', undefined)}
                  className="bg-purple-500/20 text-purple-400"
                />
              )}
              {filters.minEcMove !== undefined && (
                <FilterBadge
                  label={`EC ≥ ${filters.minEcMove}`}
                  onRemove={() => setFilter('minEcMove', undefined)}
                  className="bg-cyan-500/20 text-cyan-400"
                />
              )}
              {filters.minRsi !== undefined && (
                <FilterBadge
                  label={`RSI ≥ ${filters.minRsi}`}
                  onRemove={() => setFilter('minRsi', undefined)}
                  className="bg-orange-500/20 text-orange-400"
                />
              )}
              {filters.maxRsi !== undefined && (
                <FilterBadge
                  label={`RSI ≤ ${filters.maxRsi}`}
                  onRemove={() => setFilter('maxRsi', undefined)}
                  className="bg-orange-500/20 text-orange-400"
                />
              )}
              {filters.minDiPlus !== undefined && (
                <FilterBadge
                  label={`DI+ ≥ ${filters.minDiPlus}`}
                  onRemove={() => setFilter('minDiPlus', undefined)}
                  className="bg-green-500/20 text-green-400"
                />
              )}
              {filters.maxDiPlus !== undefined && (
                <FilterBadge
                  label={`DI+ ≤ ${filters.maxDiPlus}`}
                  onRemove={() => setFilter('maxDiPlus', undefined)}
                  className="bg-green-500/20 text-green-400"
                />
              )}
              {filters.minDiMinus !== undefined && (
                <FilterBadge
                  label={`DI- ≥ ${filters.minDiMinus}`}
                  onRemove={() => setFilter('minDiMinus', undefined)}
                  className="bg-red-500/20 text-red-400"
                />
              )}
              {filters.maxDiMinus !== undefined && (
                <FilterBadge
                  label={`DI- ≤ ${filters.maxDiMinus}`}
                  onRemove={() => setFilter('maxDiMinus', undefined)}
                  className="bg-red-500/20 text-red-400"
                />
              )}
              {filters.minProfit !== undefined && (
                <FilterBadge
                  label={`Profit ≥ ${filters.minProfit}%`}
                  onRemove={() => setFilter('minProfit', undefined)}
                  className="bg-emerald-500/20 text-emerald-400"
                />
              )}
              {filters.maxProfit !== undefined && (
                <FilterBadge
                  label={`Profit ≤ ${filters.maxProfit}%`}
                  onRemove={() => setFilter('maxProfit', undefined)}
                  className="bg-emerald-500/20 text-emerald-400"
                />
              )}
              {filters.minAdx !== undefined && (
                <FilterBadge
                  label={`ADX ≥ ${filters.minAdx}`}
                  onRemove={() => setFilter('minAdx', undefined)}
                  className="bg-amber-500/20 text-amber-400"
                />
              )}
              {filters.maxAdx !== undefined && (
                <FilterBadge
                  label={`ADX ≤ ${filters.maxAdx}`}
                  onRemove={() => setFilter('maxAdx', undefined)}
                  className="bg-amber-500/20 text-amber-400"
                />
              )}
              {filters.minVolPct !== undefined && (
                <FilterBadge
                  label={`Vol ≥ ${filters.minVolPct}%`}
                  onRemove={() => setFilter('minVolPct', undefined)}
                  className="bg-cyan-500/20 text-cyan-400"
                />
              )}
              {filters.maxVolPct !== undefined && (
                <FilterBadge
                  label={`Vol ≤ ${filters.maxVolPct}%`}
                  onRemove={() => setFilter('maxVolPct', undefined)}
                  className="bg-cyan-500/20 text-cyan-400"
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function FilterBadge({
  label,
  onRemove,
  className = 'bg-gray-700 text-gray-300'
}: {
  label: string
  onRemove: () => void
  className?: string
}) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${className}`}>
      {label}
      <button
        onClick={onRemove}
        className="hover:text-white transition-colors"
      >
        <X className="w-3 h-3" />
      </button>
    </span>
  )
}

export default AdvancedFilters
