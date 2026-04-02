'use client'

import { useState, useEffect, useCallback } from 'react'
import { Shield, Play, CheckCircle, XCircle, Handshake, ChevronDown, ChevronUp, Loader2, RefreshCw, Zap } from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────

interface AuditPoint {
  id: number
  title: string
  evidence: string
  recommendation: string
  priority: number
}

interface Exchange {
  role: 'claude' | 'openclaw' | 'system'
  content: string
}

interface Discussion {
  point_id: number
  conversation_id?: string
  exchanges: Exchange[]
  decision: 'ACCORD' | 'DESACCORD' | 'COMPROMIS'
  decision_reason: string
}

interface AuditSummary {
  id: string
  status: string
  name: string | null
  audit_type: string | null
  created_at: string
  updated_at: string
}

interface AuditFull {
  id: string
  status: string
  name: string | null
  audit_type: string | null
  report: string
  points: AuditPoint[]
  discussion: Discussion[]
  decisions_summary: string | null
  changes_applied: any[]
  created_at: string
  updated_at: string
}

// ─── Status Badge ────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending_user: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    confirmed: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    negotiating: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    pending_final: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    applied: 'bg-green-500/15 text-green-400 border-green-500/30',
    rolled_back: 'bg-red-500/15 text-red-400 border-red-500/30',
  }
  const labels: Record<string, string> = {
    pending_user: 'En attente',
    confirmed: 'Confirme',
    negotiating: 'Negociation...',
    pending_final: 'Pret a appliquer',
    applied: 'Applique',
    rolled_back: 'Annule',
  }

  return (
    <span className={`px-2 py-0.5 text-xs rounded-full border ${styles[status] || 'bg-gray-500/15 text-gray-400 border-gray-500/30'}`}>
      {labels[status] || status}
    </span>
  )
}

// ─── Priority Badge ──────────────────────────────────────────

function PriorityBadge({ priority }: { priority: number }) {
  const color = priority >= 8 ? 'text-red-400 bg-red-500/15' : priority >= 6 ? 'text-orange-400 bg-orange-500/15' : 'text-blue-400 bg-blue-500/15'
  return (
    <span className={`px-1.5 py-0.5 text-xs rounded font-mono ${color}`}>
      P{priority}
    </span>
  )
}

// ─── Decision Badge ──────────────────────────────────────────

function DecisionBadge({ decision }: { decision: string }) {
  if (decision === 'ACCORD') return <span className="flex items-center gap-1 text-xs text-green-400"><CheckCircle className="w-3.5 h-3.5" /> ACCORD</span>
  if (decision === 'COMPROMIS') return <span className="flex items-center gap-1 text-xs text-yellow-400"><Handshake className="w-3.5 h-3.5" /> COMPROMIS</span>
  if (decision === 'DESACCORD') return <span className="flex items-center gap-1 text-xs text-red-400"><XCircle className="w-3.5 h-3.5" /> DESACCORD</span>
  return <span className="text-xs text-gray-400">{decision}</span>
}

// ─── Discussion Point Card ───────────────────────────────────

function PointCard({ point, discussion }: { point: AuditPoint; discussion?: Discussion }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-800/80 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <PriorityBadge priority={point.priority} />
          <span className="text-sm font-medium text-gray-200">
            #{point.id} {point.title}
          </span>
          {discussion && <DecisionBadge decision={discussion.decision} />}
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 space-y-4">
          {/* Evidence */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">Evidence</h4>
            <p className="text-sm text-gray-300 whitespace-pre-line">{point.evidence}</p>
          </div>

          {/* Recommendation */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">Recommandation</h4>
            <p className="text-sm text-gray-300">{point.recommendation}</p>
          </div>

          {/* Exchanges */}
          {discussion && discussion.exchanges.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Discussion</h4>
              <div className="space-y-3">
                {discussion.exchanges.map((exchange, i) => (
                  <div
                    key={i}
                    className={`flex gap-3 ${exchange.role === 'openclaw' ? 'flex-row-reverse' : ''}`}
                  >
                    <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-lg">
                      {exchange.role === 'claude' ? (
                        <span title="Auditeur (Claude)">&#x1F9D1;</span>
                      ) : exchange.role === 'openclaw' ? (
                        <span title="OpenClaw">&#x1F43E;</span>
                      ) : (
                        <span>&#x2699;</span>
                      )}
                    </div>
                    <div
                      className={`flex-1 rounded-lg p-3 text-sm ${
                        exchange.role === 'claude'
                          ? 'bg-blue-500/10 border border-blue-500/20 text-gray-300'
                          : exchange.role === 'openclaw'
                            ? 'bg-purple-500/10 border border-purple-500/20 text-gray-300'
                            : 'bg-gray-700/50 border border-gray-600 text-gray-400'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1 opacity-60">
                        {exchange.role === 'claude' ? 'Auditeur' : exchange.role === 'openclaw' ? 'OpenClaw' : 'Systeme'}
                      </div>
                      <div className="whitespace-pre-line">{exchange.content}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final Decision */}
          {discussion && (
            <div className={`p-3 rounded-lg border ${
              discussion.decision === 'ACCORD'
                ? 'bg-green-500/10 border-green-500/20'
                : discussion.decision === 'COMPROMIS'
                  ? 'bg-yellow-500/10 border-yellow-500/20'
                  : 'bg-red-500/10 border-red-500/20'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <DecisionBadge decision={discussion.decision} />
                <span className="text-xs text-gray-400">Decision finale</span>
              </div>
              <p className="text-sm text-gray-300">{discussion.decision_reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Audit Tab ──────────────────────────────────────────

export default function AuditTab() {
  const [audits, setAudits] = useState<AuditSummary[]>([])
  const [selectedAudit, setSelectedAudit] = useState<AuditFull | null>(null)
  const [loading, setLoading] = useState(false)
  const [starting, setStarting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [showAddPoint, setShowAddPoint] = useState(false)
  const [newPointTitle, setNewPointTitle] = useState('')
  const [newPointEvidence, setNewPointEvidence] = useState('')
  const [newPointReco, setNewPointReco] = useState('')
  const [newPointPriority, setNewPointPriority] = useState(7)
  const [editedPoints, setEditedPoints] = useState<AuditPoint[] | null>(null)

  // Initialize editedPoints when audit loads
  useEffect(() => {
    if (selectedAudit?.points && !editedPoints) {
      setEditedPoints([...selectedAudit.points])
    }
  }, [selectedAudit?.id])

  const addCustomPoint = () => {
    if (!newPointTitle.trim()) return
    const maxId = Math.max(0, ...(editedPoints || []).map(p => p.id))
    const newPoint: AuditPoint = {
      id: maxId + 1,
      title: newPointTitle.trim(),
      evidence: newPointEvidence.trim() || 'Ajoute par l\'utilisateur',
      recommendation: newPointReco.trim() || 'A discuter avec OpenClaw',
      priority: newPointPriority,
    }
    setEditedPoints(prev => [...(prev || []), newPoint].sort((a, b) => b.priority - a.priority))
    setNewPointTitle('')
    setNewPointEvidence('')
    setNewPointReco('')
    setNewPointPriority(7)
    setShowAddPoint(false)
  }

  const removePoint = (pointId: number) => {
    setEditedPoints(prev => (prev || []).filter(p => p.id !== pointId))
  }
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load audit list
  const loadAudits = useCallback(async () => {
    try {
      const res = await fetch('/api/openclaw/audit')
      const data = await res.json()
      if (data.audits) {
        setAudits(data.audits)
      } else if (data.error) {
        setError(data.error)
      }
    } catch {
      setError('Impossible de charger les audits')
    }
  }, [])

  // Load a specific audit
  const loadAudit = useCallback(async (id: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/openclaw/audit?id=${id}`)
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        setSelectedAudit(data)
      }
    } catch {
      setError('Impossible de charger l\'audit')
    } finally {
      setLoading(false)
    }
  }, [])

  // Delete an audit (only if pending_user)
  const deleteAudit = async (auditId: string) => {
    if (!confirm('Supprimer cet audit ?')) return
    try {
      await fetch('/api/openclaw/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete', audit_id: auditId }),
      })
      if (selectedAudit?.id === auditId) setSelectedAudit(null)
      await loadAudits()
    } catch {}
  }

  // Rename an audit
  const renameAudit = async (auditId: string) => {
    const name = prompt('Nouveau nom pour cet audit:')
    if (!name?.trim()) return
    try {
      await fetch('/api/openclaw/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'rename', audit_id: auditId, name: name.trim() }),
      })
      await loadAudits()
      if (selectedAudit?.id === auditId) await loadAudit(auditId)
    } catch {}
  }

  // Start a new audit
  const startAudit = async () => {
    setStarting(true)
    setError(null)
    try {
      const res = await fetch('/api/openclaw/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'start' }),
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else if (data.audit_id) {
        await loadAudits()
        await loadAudit(data.audit_id)
      }
    } catch {
      setError('Erreur lors du lancement de l\'audit')
    } finally {
      setStarting(false)
    }
  }

  // Confirm audit (start negotiation)
  const confirmAudit = async () => {
    if (!selectedAudit) return
    setConfirming(true)
    setError(null)
    try {
      const res = await fetch('/api/openclaw/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'confirm',
          audit_id: selectedAudit.id,
          points: editedPoints || selectedAudit.points,  // Send user-modified points
        }),
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        // Reload to see updated status
        await loadAudit(selectedAudit.id)
      }
    } catch {
      setError('Erreur lors de la confirmation')
    } finally {
      setConfirming(false)
    }
  }

  // Apply decisions
  const applyDecisions = async () => {
    if (!selectedAudit) return
    setApplying(true)
    setError(null)
    try {
      const res = await fetch('/api/openclaw/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'apply', audit_id: selectedAudit.id }),
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        await loadAudit(selectedAudit.id)
      }
    } catch {
      setError('Erreur lors de l\'application')
    } finally {
      setApplying(false)
    }
  }

  const rollbackAudit = async () => {
    if (!selectedAudit) return
    if (!confirm('Annuler TOUTES les decisions appliquees par cet audit ? Les insights, blacklists et engagements seront supprimes et l\'etat precedent sera restaure.')) return
    setApplying(true)
    setError(null)
    try {
      const res = await fetch('/api/openclaw/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'rollback', audit_id: selectedAudit.id }),
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        await loadAudit(selectedAudit.id)
        await loadAudits()
      }
    } catch {
      setError('Erreur lors du rollback')
    } finally {
      setApplying(false)
    }
  }

  // Initial load
  useEffect(() => {
    loadAudits()
  }, [loadAudits])

  // Auto-refresh during negotiation
  useEffect(() => {
    if (!selectedAudit || selectedAudit.status !== 'negotiating') return

    const interval = setInterval(async () => {
      await loadAudit(selectedAudit.id)
    }, 10000)

    return () => clearInterval(interval)
  }, [selectedAudit?.id, selectedAudit?.status, loadAudit])

  // Build discussion map
  const discussionMap = new Map<number, Discussion>()
  if (selectedAudit?.discussion) {
    for (const d of selectedAudit.discussion) {
      discussionMap.set(d.point_id, d)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-semibold text-gray-200">Audit & Negociation</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadAudits}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-400 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            onClick={startAudit}
            disabled={starting}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs bg-purple-600 hover:bg-purple-500 disabled:bg-purple-800 disabled:opacity-50 rounded-lg text-white font-medium transition-colors"
          >
            {starting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            Lancer un Audit
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">Fermer</button>
        </div>
      )}

      {/* Audit List */}
      {!selectedAudit && (
        <div className="space-y-2">
          {audits.length === 0 && !error && (
            <div className="text-center py-12 text-gray-500">
              <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Aucun audit pour le moment.</p>
              <p className="text-xs mt-1">Lancez un audit pour analyser la performance d'OpenClaw.</p>
            </div>
          )}
          {audits.map(audit => (
            <div key={audit.id} className="flex items-center gap-2 p-4 bg-gray-800/50 border border-gray-700 rounded-lg hover:bg-gray-800/80 transition-colors">
              <button
                onClick={() => loadAudit(audit.id)}
                className="flex-1 flex items-center gap-3 text-left"
              >
                <div className="flex-1">
                  <span className="text-sm font-medium text-gray-200">
                    {audit.name || `Audit ${audit.audit_type === 'decisions' ? 'Decisions' : 'Portfolio'}`}
                  </span>
                  <span className="ml-2 text-xs text-gray-500">
                    {new Date(audit.created_at).toLocaleString('fr-FR')}
                  </span>
                </div>
                <StatusBadge status={audit.status} />
              </button>
              {/* Rename button */}
              <button
                onClick={(e) => { e.stopPropagation(); renameAudit(audit.id) }}
                className="p-1.5 text-gray-500 hover:text-purple-400 transition-colors"
                title="Renommer"
              >
                ✏️
              </button>
              {/* Delete button (only if not yet negotiating) */}
              {audit.status !== 'applied' && (
                <button
                  onClick={(e) => { e.stopPropagation(); deleteAudit(audit.id) }}
                  className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                  title="Supprimer"
                >
                  🗑️
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Selected Audit Detail */}
      {selectedAudit && (
        <div className="space-y-4">
          {/* Back + Status */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSelectedAudit(null)}
              className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              &larr; Retour a la liste
            </button>
            <div className="flex items-center gap-3">
              <StatusBadge status={selectedAudit.status} />
              {selectedAudit.status === 'negotiating' && (
                <span className="flex items-center gap-1 text-xs text-purple-400">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {selectedAudit.discussion?.length || 0}/{selectedAudit.points?.length || 0} points traites
                </span>
              )}
            </div>
          </div>

          {/* Phase 1: Report */}
          {selectedAudit.report && (
            <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Rapport d'Audit</h3>
              <div className="text-sm text-gray-400 whitespace-pre-line max-h-96 overflow-y-auto prose prose-invert prose-sm">
                {selectedAudit.report}
              </div>
            </div>
          )}

          {/* Phase 2: Edit Points + Confirm */}
          {selectedAudit.status === 'pending_user' && (
            <div className="space-y-4">
              {/* Editable Points List */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-300">
                    Points a discuter ({(editedPoints || selectedAudit.points).length})
                  </h3>
                  <button
                    onClick={() => setShowAddPoint(!showAddPoint)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-purple-500/20 border border-purple-500/40 text-purple-300 hover:bg-purple-500/30 rounded-lg transition-colors"
                  >
                    {showAddPoint ? '✕ Annuler' : '+ Ajouter un point'}
                  </button>
                </div>

                {/* Add Point Form */}
                {showAddPoint && (
                  <div className="mb-4 p-4 bg-gray-800/50 border border-purple-500/20 rounded-lg space-y-3">
                    <input
                      type="text"
                      placeholder="Titre du point (ex: Tester un SL plus large)"
                      value={newPointTitle}
                      onChange={e => setNewPointTitle(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    />
                    <textarea
                      placeholder="Evidence / contexte (optionnel)"
                      value={newPointEvidence}
                      onChange={e => setNewPointEvidence(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    />
                    <textarea
                      placeholder="Recommandation / question pour OpenClaw"
                      value={newPointReco}
                      onChange={e => setNewPointReco(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    />
                    <div className="flex items-center gap-3">
                      <label className="text-xs text-gray-400">Priorite:</label>
                      {[5, 6, 7, 8, 9].map(p => (
                        <button
                          key={p}
                          onClick={() => setNewPointPriority(p)}
                          className={`px-2 py-1 text-xs rounded font-mono transition-colors ${
                            newPointPriority === p
                              ? p >= 8 ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                                : p >= 6 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                                : 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                              : 'bg-gray-800 text-gray-500 border border-gray-700'
                          }`}
                        >
                          P{p}
                        </button>
                      ))}
                      <button
                        onClick={addCustomPoint}
                        disabled={!newPointTitle.trim()}
                        className="ml-auto flex items-center gap-1.5 px-4 py-1.5 text-xs bg-purple-600 hover:bg-purple-500 disabled:opacity-30 rounded-lg text-white font-medium transition-colors"
                      >
                        <CheckCircle className="w-3.5 h-3.5" /> Ajouter
                      </button>
                    </div>
                  </div>
                )}

                {/* Points List (editable) */}
                <div className="space-y-2">
                  {(editedPoints || selectedAudit.points).map(point => (
                    <div key={point.id} className="flex items-start gap-3 p-3 bg-gray-800/50 border border-gray-700 rounded-lg">
                      <PriorityBadge priority={point.priority} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200">{point.title}</p>
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">{point.evidence}</p>
                        <p className="text-xs text-purple-400 mt-1">{point.recommendation}</p>
                      </div>
                      <button
                        onClick={() => removePoint(point.id)}
                        className="p-1 text-gray-600 hover:text-red-400 transition-colors"
                        title="Supprimer ce point"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Confirm Button */}
              <div className="flex items-center gap-3 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <span className="text-sm text-yellow-300">
                  {(editedPoints || selectedAudit.points).length} point(s) a negocier avec OpenClaw
                </span>
                <button
                  onClick={confirmAudit}
                  disabled={confirming || (editedPoints || selectedAudit.points).length === 0}
                  className="flex items-center gap-1.5 px-4 py-1.5 text-xs bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 rounded-lg text-white font-medium transition-colors ml-auto"
                >
                  {confirming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  Confirmer & Lancer la Negociation
                </button>
              </div>
            </div>
          )}

          {/* Phase 3: Discussion Points */}
          {selectedAudit.points && selectedAudit.points.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-300">
                Points de Discussion ({selectedAudit.points.length})
              </h3>
              {selectedAudit.points.map(point => (
                <PointCard
                  key={point.id}
                  point={point}
                  discussion={discussionMap.get(point.id)}
                />
              ))}
            </div>
          )}

          {/* Decisions Summary */}
          {selectedAudit.decisions_summary && (
            <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">Resume des Decisions</h3>
              <div className="text-sm text-gray-400 whitespace-pre-line">
                {selectedAudit.decisions_summary}
              </div>
            </div>
          )}

          {/* Phase 4: Apply */}
          {selectedAudit.status === 'pending_final' && (
            <div className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
              <span className="text-sm text-green-300">Negociation terminee. Appliquer les decisions ?</span>
              <button
                onClick={applyDecisions}
                disabled={applying}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-lg text-white font-medium transition-colors"
              >
                {applying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                Appliquer les Decisions
              </button>
            </div>
          )}

          {/* Applied Changes */}
          {selectedAudit.changes_applied && selectedAudit.changes_applied.length > 0 && (
            <div className="bg-gray-800/30 border border-gray-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-300">Changements Appliques</h3>
                {selectedAudit.status === 'applied' && (
                  <button
                    onClick={rollbackAudit}
                    disabled={applying}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 rounded-lg transition-colors"
                  >
                    {applying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
                    Rollback — Annuler tout
                  </button>
                )}
              </div>
              <div className="space-y-1">
                {selectedAudit.changes_applied.map((change: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    {change.applied ? (
                      <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                    )}
                    <span className={change.applied ? 'text-gray-300' : 'text-gray-500'}>
                      {change.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rolled back notice */}
          {selectedAudit.status === 'rolled_back' && (
            <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
              <XCircle className="w-5 h-5 text-red-400" />
              <span className="text-sm text-red-300">Cet audit a ete annule (rollback). Toutes les decisions ont ete restaurees a l'etat precedent.</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
