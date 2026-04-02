'use client'

import { BarChart3, TrendingUp, Zap } from 'lucide-react'

interface FilteredStatsProps {
  total: number
  filtered: number
  alerts: Array<{
    scanner_score: number
    pp?: boolean
    ec?: boolean
    decisions?: Array<{ p_success?: number | null }> | null
  }>
}

export function FilteredStats({ total, filtered, alerts }: FilteredStatsProps) {
  const avgScore = alerts.length > 0
    ? (alerts.reduce((s, a) => s + a.scanner_score, 0) / alerts.length).toFixed(1)
    : '0'
  const ppCount = alerts.filter(a => a.pp).length
  const ecCount = alerts.filter(a => a.ec).length
  const withDecision = alerts.filter(a => a.decisions?.[0]?.p_success != null)
  const avgPSuccess = withDecision.length > 0
    ? (withDecision.reduce((s, a) => s + (a.decisions![0].p_success || 0), 0) / withDecision.length * 100).toFixed(0)
    : null

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <div className="bg-gray-800/50 rounded-lg p-3 text-center">
        <div className="text-xs text-gray-500 mb-1">Alertes</div>
        <div className="text-lg font-bold text-white">{filtered}<span className="text-sm text-gray-500">/{total}</span></div>
      </div>
      <div className="bg-gray-800/50 rounded-lg p-3 text-center">
        <div className="text-xs text-gray-500 mb-1">Score Moy.</div>
        <div className="text-lg font-bold text-yellow-400">{avgScore}/10</div>
      </div>
      <div className="bg-gray-800/50 rounded-lg p-3 text-center">
        <div className="text-xs text-gray-500 mb-1">PP Buy</div>
        <div className="text-lg font-bold text-green-400">{ppCount}</div>
      </div>
      <div className="bg-gray-800/50 rounded-lg p-3 text-center">
        <div className="text-xs text-gray-500 mb-1">Entry Confirm</div>
        <div className="text-lg font-bold text-blue-400">{ecCount}</div>
      </div>
      {avgPSuccess !== null && (
        <div className="bg-gray-800/50 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">P(success) Moy.</div>
          <div className={`text-lg font-bold ${Number(avgPSuccess) >= 50 ? 'text-green-400' : 'text-red-400'}`}>{avgPSuccess}%</div>
        </div>
      )}
    </div>
  )
}
