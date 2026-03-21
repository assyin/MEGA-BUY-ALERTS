'use client'

import { useState, useEffect, useMemo } from 'react'
import { Brain, Database, TrendingUp, AlertTriangle, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react"
import { supabase } from '@/lib/supabase'
import { DecisionsTable } from "@/components/DecisionsTable"
import { ModelInfo } from "@/components/ModelInfo"
import { AdvancedFilters } from "@/components/AdvancedFilters"
import { FilteredStats } from "@/components/FilteredStats"
import { useAdvancedFilters } from '@/hooks/useAdvancedFilters'
import { filterAlerts } from '@/lib/filterAlerts'
import { Alert, Decision, Outcome, LLMReport } from "@/types/database"

interface AlertWithData extends Alert {
  decisions: Decision[]
  outcomes: Outcome[]
  llm_reports: LLMReport[]
  decision?: string
  [key: string]: unknown
}

const ITEMS_PER_PAGE = 25

export default function DecisionsPageClient() {
  const [alertsWithData, setAlertsWithData] = useState<AlertWithData[]>([])
  const [stats, setStats] = useState({
    totalDecisions: 0,
    tradeDecisions: 0,
    watchDecisions: 0,
    skipDecisions: 0,
    successOutcomes: 0,
    failOutcomes: 0,
    v2Decisions: 0,
    llmReports: 0,
    successRate: 0
  })
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)

  // Advanced filters
  const { filters } = useAdvancedFilters()

  // Load data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        // Fetch all data in parallel
        const [alertsRes, decisionsRes, outcomesRes, llmReportsRes] = await Promise.all([
          supabase.from("alerts").select("*").order("created_at", { ascending: false }).limit(500),
          supabase.from("decisions").select("*"),
          supabase.from("outcomes").select("*"),
          supabase.from("llm_reports").select("*")
        ])

        const alerts = (alertsRes.data || []) as Alert[]
        const decisions = (decisionsRes.data || []) as Decision[]
        const outcomes = (outcomesRes.data || []) as Outcome[]
        const llmReports = (llmReportsRes.data || []) as LLMReport[]

        // Create lookup maps
        const decisionsMap = new Map(decisions.map(d => [d.alert_id, d]))
        const outcomesMap = new Map(outcomes.map(o => [o.alert_id, o]))
        const llmReportsMap = new Map(llmReports.map(r => [r.alert_id, r]))

        // Join data
        const joinedAlerts: AlertWithData[] = alerts.map(alert => ({
          ...alert,
          decisions: decisionsMap.has(alert.id) ? [decisionsMap.get(alert.id)!] : [],
          outcomes: outcomesMap.has(alert.id) ? [outcomesMap.get(alert.id)!] : [],
          llm_reports: llmReportsMap.has(alert.id) ? [llmReportsMap.get(alert.id)!] : [],
          decision: decisionsMap.get(alert.id)?.decision
        }))

        setAlertsWithData(joinedAlerts)

        // Calculate stats
        const totalDecisions = decisions.length
        const tradeDecisions = decisions.filter(d => d.decision === "TRADE").length
        const watchDecisions = decisions.filter(d => d.decision === "WATCH").length
        const skipDecisions = decisions.filter(d => d.decision === "SKIP").length
        const successOutcomes = outcomes.filter(o => (o.max_profit_pct || 0) >= 2).length
        const failOutcomes = outcomes.filter(o => o.max_profit_pct !== null && (o.max_profit_pct || 0) < 2).length
        const v2Decisions = decisions.filter(d => d.model_version === "2.0.0").length

        setStats({
          totalDecisions,
          tradeDecisions,
          watchDecisions,
          skipDecisions,
          successOutcomes,
          failOutcomes,
          v2Decisions,
          llmReports: llmReports.length,
          successRate: failOutcomes + successOutcomes > 0
            ? (successOutcomes / (successOutcomes + failOutcomes) * 100)
            : 0
        })
      } catch (error) {
        console.error('Error loading data:', error)
      }
      setLoading(false)
    }
    loadData()
  }, [])

  // Apply advanced filters
  const filteredAlerts = useMemo(() => {
    return filterAlerts(alertsWithData, filters)
  }, [alertsWithData, filters])

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters])

  // Pagination
  const totalPages = Math.ceil(filteredAlerts.length / ITEMS_PER_PAGE)
  const paginatedAlerts = filteredAlerts.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/10 rounded-lg">
            <Brain className="w-6 h-6 text-purple-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">ML Decisions</h1>
            <p className="text-gray-400 text-sm">
              {loading ? 'Chargement...' : `${alertsWithData.length} alertes avec decisions ML`}
            </p>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-gray-400" />
            <span className="text-gray-400 text-sm">Total</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats.totalDecisions}</p>
        </div>

        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-green-400 text-sm">TRADE</span>
          </div>
          <p className="text-2xl font-bold text-green-400">{stats.tradeDecisions}</p>
        </div>

        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            <span className="text-yellow-400 text-sm">WATCH</span>
          </div>
          <p className="text-2xl font-bold text-yellow-400">{stats.watchDecisions}</p>
        </div>

        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-red-400 text-sm">SKIP</span>
          </div>
          <p className="text-2xl font-bold text-red-400">{stats.skipDecisions}</p>
        </div>

        <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="text-purple-400 text-sm">Model v2.0</span>
          </div>
          <p className="text-2xl font-bold text-purple-400">{stats.v2Decisions}</p>
        </div>

        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-blue-400 text-sm">Success Rate</span>
          </div>
          <p className="text-2xl font-bold text-blue-400">{stats.successRate.toFixed(1)}%</p>
        </div>

        <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-cyan-400 text-sm">LLM Reports</span>
          </div>
          <p className="text-2xl font-bold text-cyan-400">{stats.llmReports}</p>
        </div>
      </div>

      {/* Advanced Filters */}
      <AdvancedFilters resultCount={filteredAlerts.length} showDecisions={true} />

      {/* Filtered Performance Stats */}
      <FilteredStats alerts={filteredAlerts} showDecisions={true} />

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Decisions Table (3 columns) */}
        <div className="xl:col-span-3">
          {loading ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-400">
              Chargement des décisions...
            </div>
          ) : (
            <DecisionsTable alerts={paginatedAlerts} />
          )}

          {/* Pagination */}
          {!loading && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-400">
                Affichage {((currentPage - 1) * ITEMS_PER_PAGE) + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, filteredAlerts.length)} sur {filteredAlerts.length}
              </p>
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
                  Page {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="p-1 rounded bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronsRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Model Info Sidebar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Model Info
          </h2>
          <ModelInfo />
        </div>
      </div>
    </div>
  )
}
