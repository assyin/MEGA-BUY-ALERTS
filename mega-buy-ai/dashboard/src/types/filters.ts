export const EMOTIONS = ['EXTREME_FEAR', 'FEAR', 'NEUTRAL', 'GREED', 'EXTREME_GREED'] as const
export const DECISIONS = ['TRADE', 'WATCH', 'SKIP'] as const
export const TIMEFRAMES = ['15m', '30m', '1h', '4h'] as const
export const CONDITIONS = ['RSI', 'DMI', 'AST', 'CHoCH', 'Zone', 'Lazy', 'Vol', 'ST', 'PP', 'EC'] as const

export interface AdvancedFilters {
  dateStart?: string
  dateEnd?: string
  pair?: string
  minScore?: number
  maxScore?: number
  timeframes?: string[]
  conditions?: string[]
  emotions?: string[]
  decisions?: string[]
  minDiMinus?: number
  maxDiPlus?: number
  minAdx?: number
  minVolPct?: number
  minPSuccess?: number
  maxPSuccess?: number
}

export const DEFAULT_FILTERS: AdvancedFilters = {}
