import { AdvancedFilters } from '@/types/filters'

interface AlertLike {
  pair: string
  alert_timestamp: string
  scanner_score: number
  timeframes: string[]
  pp?: boolean
  ec?: boolean
  di_plus_4h?: number | null
  di_minus_4h?: number | null
  adx_4h?: number | null
  vol_pct?: Record<string, number> | null
  decision?: string
  decisions?: Array<{ p_success?: number | null; decision?: string }> | null
}

export function filterAlerts<T extends AlertLike>(alerts: T[], filters: AdvancedFilters): T[] {
  return alerts.filter(alert => {
    // Date range
    if (filters.dateStart && alert.alert_timestamp < filters.dateStart) return false
    if (filters.dateEnd && alert.alert_timestamp > filters.dateEnd + 'T23:59:59') return false

    // Pair search
    if (filters.pair && !alert.pair.toLowerCase().includes(filters.pair.toLowerCase())) return false

    // Score range
    if (filters.minScore !== undefined && alert.scanner_score < filters.minScore) return false
    if (filters.maxScore !== undefined && alert.scanner_score > filters.maxScore) return false

    // Timeframes
    if (filters.timeframes?.length) {
      const hasTf = filters.timeframes.some(tf => alert.timeframes?.includes(tf))
      if (!hasTf) return false
    }

    // Conditions (PP, EC etc.)
    if (filters.conditions?.length) {
      for (const cond of filters.conditions) {
        if (cond === 'PP' && !alert.pp) return false
        if (cond === 'EC' && !alert.ec) return false
      }
    }

    // DI/ADX filters
    if (filters.minDiMinus !== undefined && (alert.di_minus_4h ?? 0) < filters.minDiMinus) return false
    if (filters.maxDiPlus !== undefined && (alert.di_plus_4h ?? 100) > filters.maxDiPlus) return false
    if (filters.minAdx !== undefined && (alert.adx_4h ?? 0) < filters.minAdx) return false

    // Volume filter
    if (filters.minVolPct !== undefined && alert.vol_pct) {
      const maxVol = Math.max(...Object.values(alert.vol_pct))
      if (maxVol < filters.minVolPct) return false
    }

    // Decision filter
    if (filters.decisions?.length) {
      const dec = alert.decision || alert.decisions?.[0]?.decision
      if (!dec || !filters.decisions.includes(dec)) return false
    }

    // P_success filter
    if (filters.minPSuccess !== undefined || filters.maxPSuccess !== undefined) {
      const ps = alert.decisions?.[0]?.p_success
      if (ps == null) return false
      if (filters.minPSuccess !== undefined && ps < filters.minPSuccess) return false
      if (filters.maxPSuccess !== undefined && ps > filters.maxPSuccess) return false
    }

    return true
  })
}
