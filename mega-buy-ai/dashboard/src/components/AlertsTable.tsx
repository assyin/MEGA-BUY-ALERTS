'use client'

import { CheckCircle, XCircle, ExternalLink } from 'lucide-react'
import type { Alert, Decision } from '@/types/database'

interface AlertWithDecision extends Alert {
  decisions?: Decision[]
}

interface AlertsTableProps {
  alerts: AlertWithDecision[]
  onAlertClick?: (alert: AlertWithDecision) => void
}

const conditionKeys = [
  { key: 'rsi_check', label: 'RSI' },
  { key: 'dmi_check', label: 'DMI' },
  { key: 'ast_check', label: 'AST' },
  { key: 'choch', label: 'CHoCH' },
  { key: 'zone', label: 'Zone' },
  { key: 'lazy', label: 'Lazy' },
  { key: 'vol', label: 'Vol' },
  { key: 'st', label: 'ST' },
  { key: 'pp', label: 'PP' },
  { key: 'ec', label: 'EC' },
] as const

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 8 ? 'text-green-400 bg-green-500/10' : score >= 6 ? 'text-yellow-400 bg-yellow-500/10' : 'text-red-400 bg-red-500/10'
  return <span className={`px-2 py-0.5 rounded text-xs font-bold ${color}`}>{score}/10</span>
}

function formatDate(ts: string) {
  const d = new Date(ts)
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' })
}

export function AlertsTable({ alerts, onAlertClick }: AlertsTableProps) {
  if (alerts.length === 0) {
    return <div className="text-center py-8 text-gray-500">Aucune alerte trouvee</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-800 sticky top-0">
          <tr>
            <th className="px-3 py-2 text-left text-xs text-gray-400">Date</th>
            <th className="px-3 py-2 text-left text-xs text-gray-400">Paire</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">TF</th>
            <th className="px-3 py-2 text-right text-xs text-gray-400">Prix</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">Score</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">Conditions</th>
            <th className="px-3 py-2 text-right text-xs text-gray-400">DI+</th>
            <th className="px-3 py-2 text-right text-xs text-gray-400">DI-</th>
            <th className="px-3 py-2 text-right text-xs text-gray-400">ADX</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">LZ</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">EC</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">P(success)</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => {
            const decision = alert.decisions?.[0]
            const pSuccess = decision?.p_success
            const volMax = alert.vol_pct ? Math.max(...Object.values(alert.vol_pct)) : null

            return (
              <tr
                key={alert.id}
                className="border-t border-gray-800 hover:bg-gray-800/70 cursor-pointer transition-colors"
                onClick={() => onAlertClick?.(alert)}
              >
                <td className="px-3 py-2 text-gray-300 whitespace-nowrap text-xs">
                  {formatDate(alert.alert_timestamp)}
                </td>
                <td className="px-3 py-2">
                  <span className="font-medium text-white">{alert.pair.replace('USDT', '')}</span>
                  <span className="text-gray-500 text-xs">USDT</span>
                </td>
                <td className="px-3 py-2 text-center">
                  <div className="flex gap-0.5 justify-center">
                    {alert.timeframes?.map(tf => (
                      <span key={tf} className="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded">{tf}</span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2 text-right font-mono text-gray-300 text-xs">
                  {alert.price < 1 ? alert.price.toFixed(6) : alert.price < 100 ? alert.price.toFixed(4) : alert.price.toFixed(2)}
                </td>
                <td className="px-3 py-2 text-center">
                  <ScoreBadge score={alert.scanner_score} />
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-0.5 justify-center flex-wrap">
                    {conditionKeys.map(({ key, label }) => {
                      const val = alert[key as keyof typeof alert]
                      return (
                        <span
                          key={key}
                          className={`w-5 h-5 flex items-center justify-center rounded text-[9px] font-bold ${
                            val ? 'bg-green-500/20 text-green-400' : 'bg-gray-700/50 text-gray-600'
                          }`}
                          title={`${label}: ${val ? 'YES' : 'NO'}`}
                        >
                          {label.charAt(0)}
                        </span>
                      )
                    })}
                  </div>
                </td>
                <td className="px-3 py-2 text-right text-xs">
                  <span className={alert.di_plus_4h && alert.di_plus_4h > 25 ? 'text-green-400' : 'text-gray-400'}>
                    {alert.di_plus_4h?.toFixed(1) ?? '-'}
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-xs">
                  <span className={alert.di_minus_4h && alert.di_minus_4h >= 22 ? 'text-yellow-400' : 'text-gray-400'}>
                    {alert.di_minus_4h?.toFixed(1) ?? '-'}
                  </span>
                </td>
                <td className="px-3 py-2 text-right text-xs">
                  <span className={alert.adx_4h && alert.adx_4h >= 25 ? 'text-green-400' : 'text-gray-400'}>
                    {alert.adx_4h?.toFixed(1) ?? '-'}
                  </span>
                </td>
                <td className="px-3 py-2 text-center">
                  {alert.lazy_values ? (
                    <div className="flex gap-0.5 justify-center">
                      {['15m', '30m', '1h', '4h'].map(tf => {
                        const v = alert.lazy_values?.[tf]
                        const move = alert.lazy_moves?.[tf]
                        if (!v && !move) return <span key={tf} className="text-gray-700 text-[9px]">-</span>
                        const isRed = v?.includes('Red') || move === '🔴'
                        const isYellow = v?.includes('Yellow') || move === '🟡'
                        return (
                          <span key={tf} className={`px-1 py-0.5 rounded text-[9px] font-mono ${
                            isRed ? 'bg-red-500/20 text-red-400' : isYellow ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-700/50 text-gray-500'
                          }`} title={`LZ ${tf}: ${v || move || '-'}`}>
                            {v ? v.split(' ')[0] : move || '-'}
                          </span>
                        )
                      })}
                    </div>
                  ) : <span className="text-gray-700 text-xs">-</span>}
                </td>
                <td className="px-3 py-2 text-center">
                  {alert.ec_moves ? (
                    <div className="flex gap-0.5 justify-center">
                      {['15m', '30m', '1h', '4h'].map(tf => {
                        const v = alert.ec_moves?.[tf]
                        if (v == null) return <span key={tf} className="text-gray-700 text-[9px]">-</span>
                        return (
                          <span key={tf} className={`px-1 py-0.5 rounded text-[9px] font-mono ${
                            v >= 4 ? 'bg-green-500/20 text-green-400' : v > 0 ? 'bg-gray-700/50 text-gray-400' : 'bg-red-500/10 text-red-400'
                          }`} title={`EC ${tf}: ${v.toFixed(1)}`}>
                            {v > 0 ? '+' : ''}{v.toFixed(0)}
                          </span>
                        )
                      })}
                    </div>
                  ) : <span className="text-gray-700 text-xs">-</span>}
                </td>
                <td className="px-3 py-2 text-center">
                  {pSuccess != null ? (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      pSuccess >= 0.5 ? 'bg-green-500/10 text-green-400' :
                      pSuccess >= 0.3 ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>
                      {(pSuccess * 100).toFixed(0)}%
                    </span>
                  ) : (
                    <span className="text-gray-600 text-xs">-</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
