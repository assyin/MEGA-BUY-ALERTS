'use client'

import type { Alert, Decision, Outcome } from '@/types/database'

interface AlertWithData extends Alert {
  decisions: Decision[]
  outcomes?: Outcome[]
}

interface DecisionsTableProps {
  alerts: AlertWithData[]
  onAlertClick?: (alert: AlertWithData) => void
}

function formatDate(ts: string) {
  return new Date(ts).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function DecisionsTable({ alerts, onAlertClick }: DecisionsTableProps) {
  if (alerts.length === 0) {
    return <div className="text-center py-8 text-gray-500">Aucune decision trouvee</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-800 sticky top-0">
          <tr>
            <th className="px-3 py-2 text-left text-xs text-gray-400">Date</th>
            <th className="px-3 py-2 text-left text-xs text-gray-400">Paire</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">Score</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">Decision</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">P(success)</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">Confidence</th>
            <th className="px-3 py-2 text-center text-xs text-gray-400">Outcome</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => {
            const dec = alert.decisions?.[0]
            const outcome = alert.outcomes?.[0]
            return (
              <tr
                key={alert.id}
                className="border-t border-gray-800 hover:bg-gray-800/70 cursor-pointer transition-colors"
                onClick={() => onAlertClick?.(alert)}
              >
                <td className="px-3 py-2 text-gray-300 whitespace-nowrap text-xs">{formatDate(alert.alert_timestamp)}</td>
                <td className="px-3 py-2 font-medium text-white">{alert.pair}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    alert.scanner_score >= 8 ? 'text-green-400 bg-green-500/10' : alert.scanner_score >= 6 ? 'text-yellow-400 bg-yellow-500/10' : 'text-red-400 bg-red-500/10'
                  }`}>{alert.scanner_score}/10</span>
                </td>
                <td className="px-3 py-2 text-center">
                  {dec?.decision ? (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      dec.decision === 'TRADE' ? 'bg-green-500/10 text-green-400' :
                      dec.decision === 'WATCH' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>{dec.decision}</span>
                  ) : <span className="text-gray-600 text-xs">-</span>}
                </td>
                <td className="px-3 py-2 text-center">
                  {dec?.p_success != null ? (
                    <span className={`text-xs font-mono ${dec.p_success >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                      {(dec.p_success * 100).toFixed(0)}%
                    </span>
                  ) : <span className="text-gray-600 text-xs">-</span>}
                </td>
                <td className="px-3 py-2 text-center">
                  {dec?.confidence != null ? (
                    <span className="text-xs text-gray-400">{(dec.confidence * 100).toFixed(0)}%</span>
                  ) : <span className="text-gray-600 text-xs">-</span>}
                </td>
                <td className="px-3 py-2 text-center">
                  {outcome?.result ? (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      outcome.result === 'WIN' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                    }`}>{outcome.result} {outcome.pnl_pct != null ? `(${outcome.pnl_pct > 0 ? '+' : ''}${outcome.pnl_pct.toFixed(1)}%)` : ''}</span>
                  ) : <span className="text-gray-600 text-xs">-</span>}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
