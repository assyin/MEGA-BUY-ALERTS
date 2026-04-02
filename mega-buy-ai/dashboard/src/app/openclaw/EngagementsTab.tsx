'use client'

import { useState, useEffect, useCallback } from 'react'
import { CheckCircle, XCircle, Clock, AlertTriangle, RefreshCw, Loader2, Target } from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────

interface Engagement {
  id: string
  audit_id: string
  point_id: number
  title: string
  metric_type: string
  metric_target: string
  deadline: string | null
  verification_query: string
  status: 'PENDING' | 'RESPECTED' | 'NOT_RESPECTED' | 'EXPIRED'
  verification_data: Record<string, any> | null
  checked_at: string | null
  created_at: string
}

// ─── Helpers ─────────────────────────────────────────────────

function getStatusStyle(status: string) {
  switch (status) {
    case 'RESPECTED':
      return { color: 'text-green-400', bg: 'bg-green-500/15 border-green-500/30', icon: <CheckCircle className="w-4 h-4" />, label: 'Respecte' }
    case 'NOT_RESPECTED':
      return { color: 'text-red-400', bg: 'bg-red-500/15 border-red-500/30', icon: <XCircle className="w-4 h-4" />, label: 'Non respecte' }
    case 'EXPIRED':
      return { color: 'text-gray-400', bg: 'bg-gray-500/15 border-gray-500/30', icon: <AlertTriangle className="w-4 h-4" />, label: 'Expire' }
    default:
      return { color: 'text-yellow-400', bg: 'bg-yellow-500/15 border-yellow-500/30', icon: <Clock className="w-4 h-4" />, label: 'En attente' }
  }
}

function getMetricLabel(type: string) {
  const labels: Record<string, string> = {
    tp_min_pct: 'TP Min %',
    trades_count: 'Nb Trades',
    pair_wr: 'Win Rate Pair',
    pair_blacklist: 'Blacklist',
    position_size: 'Taille Position',
    custom: 'Personnalise',
  }
  return labels[type] || type
}

function getDeadlineCountdown(deadline: string | null): { text: string; color: string } {
  if (!deadline) return { text: 'Immediat', color: 'text-gray-500' }

  const now = new Date()
  const dl = new Date(deadline)
  const diffMs = dl.getTime() - now.getTime()
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays > 1) return { text: `J-${diffDays}`, color: 'text-yellow-400' }
  if (diffDays === 1) return { text: 'J-1', color: 'text-orange-400' }
  if (diffDays === 0) return { text: "Aujourd'hui", color: 'text-orange-400' }
  if (diffDays === -1) return { text: 'J+1 retard', color: 'text-red-400' }
  return { text: `J+${Math.abs(diffDays)} retard`, color: 'text-red-400' }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// ─── Component ───────────────────────────────────────────────

export default function EngagementsTab() {
  const [engagements, setEngagements] = useState<Engagement[]>([])
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [lastCheck, setLastCheck] = useState<string | null>(null)

  const fetchEngagements = useCallback(async () => {
    try {
      const res = await fetch('/api/openclaw/engagements')
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setEngagements(data.engagements || [])
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEngagements()
    const interval = setInterval(fetchEngagements, 60000) // auto-refresh 60s
    return () => clearInterval(interval)
  }, [fetchEngagements])

  const handleCheck = async () => {
    setChecking(true)
    try {
      const res = await fetch('/api/openclaw/engagements', { method: 'POST' })
      if (res.ok) {
        setLastCheck(new Date().toISOString())
        // Refresh after check
        await fetchEngagements()
      }
    } catch {
      // silent
    } finally {
      setChecking(false)
    }
  }

  // Stats
  const pending = engagements.filter(e => e.status === 'PENDING').length
  const respected = engagements.filter(e => e.status === 'RESPECTED').length
  const notRespected = engagements.filter(e => e.status === 'NOT_RESPECTED').length
  const expired = engagements.filter(e => e.status === 'EXPIRED').length

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        Chargement des engagements...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-gray-400">En attente:</span>
              <span className="text-sm font-bold text-yellow-400">{pending}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm text-gray-400">Respectes:</span>
              <span className="text-sm font-bold text-green-400">{respected}</span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-sm text-gray-400">Non respectes:</span>
              <span className="text-sm font-bold text-red-400">{notRespected}</span>
            </div>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Expires:</span>
              <span className="text-sm font-bold text-gray-400">{expired}</span>
            </div>
          </div>
        </div>

        <button
          onClick={handleCheck}
          disabled={checking}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-purple-500/20 border border-purple-500/40 text-purple-300 hover:bg-purple-500/30 transition-colors disabled:opacity-50"
        >
          {checking ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Verifier maintenant
        </button>
      </div>

      {lastCheck && (
        <p className="text-xs text-gray-500">Derniere verification manuelle: {formatDate(lastCheck)}</p>
      )}

      {/* Engagements list */}
      {engagements.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Target className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">Aucun engagement</p>
          <p className="text-sm mt-1">Les engagements sont crees automatiquement lors de l&apos;application des decisions d&apos;audit.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {engagements.map(eng => {
            const statusStyle = getStatusStyle(eng.status)
            const countdown = getDeadlineCountdown(eng.deadline)
            const vd = eng.verification_data

            return (
              <div
                key={eng.id}
                className={`rounded-lg border p-4 ${statusStyle.bg}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Title + Status */}
                    <div className="flex items-center gap-3 mb-2">
                      <span className={statusStyle.color}>{statusStyle.icon}</span>
                      <h3 className="text-sm font-semibold text-gray-200 truncate">{eng.title}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${statusStyle.bg} ${statusStyle.color}`}>
                        {statusStyle.label}
                      </span>
                    </div>

                    {/* Meta info */}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 mb-3">
                      <span className="bg-gray-800 px-2 py-0.5 rounded">{getMetricLabel(eng.metric_type)}</span>
                      <span>Cible: <span className="text-gray-300">{eng.metric_target}</span></span>
                      <span>
                        Deadline: <span className={countdown.color}>{countdown.text}</span>
                        {eng.deadline && <span className="ml-1 text-gray-600">({formatDate(eng.deadline)})</span>}
                      </span>
                      {eng.checked_at && (
                        <span>Verifie: {formatDate(eng.checked_at)}</span>
                      )}
                    </div>

                    {/* Verification query */}
                    {eng.verification_query && (
                      <p className="text-xs text-gray-500 mb-2 italic">{eng.verification_query}</p>
                    )}

                    {/* Verification data */}
                    {vd && (
                      <div className="bg-gray-900/50 rounded px-3 py-2 text-xs">
                        {vd.message && (
                          <p className="text-gray-300 mb-1">{vd.message}</p>
                        )}
                        {vd.current !== undefined && vd.target !== undefined && (
                          <div className="flex items-center gap-3">
                            <span className="text-gray-500">Actuel:</span>
                            <span className={vd.met ? 'text-green-400' : 'text-red-400'}>
                              {typeof vd.current === 'number' ? vd.current.toFixed(2) : vd.current}
                            </span>
                            <span className="text-gray-600">/</span>
                            <span className="text-gray-400">{vd.target}</span>
                            {vd.sample_size && (
                              <span className="text-gray-600">({vd.sample_size} trades)</span>
                            )}
                          </div>
                        )}
                        {vd.requires_manual && (
                          <p className="text-yellow-500 mt-1">Verification manuelle requise</p>
                        )}
                        {vd.error && (
                          <p className="text-red-500 mt-1">Erreur: {vd.error}</p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Audit source */}
                  <div className="text-right text-xs text-gray-600 shrink-0">
                    <p>Point #{eng.point_id}</p>
                    <p className="truncate max-w-[120px]" title={eng.audit_id}>
                      {eng.audit_id ? eng.audit_id.slice(0, 8) + '...' : '—'}
                    </p>
                    <p className="mt-1">{formatDate(eng.created_at)}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
