'use client'

import { useState, useEffect, useMemo } from 'react'
import { Bell, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Search } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { AlertsTable } from "@/components/AlertsTable"
import { AdvancedFilters } from "@/components/AdvancedFilters"
import { FilteredStats } from "@/components/FilteredStats"
import { useAdvancedFilters } from '@/hooks/useAdvancedFilters'
import { filterAlerts } from '@/lib/filterAlerts'
import { AlertAnalysisModal } from "@/components/AlertAnalysisModal"
import { Alert, Decision } from "@/types/database"

interface AlertWithDecision extends Alert {
  decisions?: Decision[]
}

const ITEMS_PER_PAGE = 25

export default function AlertsPageClient() {
  const [alerts, setAlerts] = useState<AlertWithDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedAlert, setSelectedAlert] = useState<AlertWithDecision | null>(null)
  const [pairSearch, setPairSearch] = useState('')

  // Advanced filters
  const { filters } = useAdvancedFilters()

  // Load ALL alerts from Supabase (paginated to bypass 1000-row limit)
  useEffect(() => {
    const loadAlerts = async () => {
      setLoading(true)
      try {
        const PAGE_SIZE = 1000
        let allAlerts: AlertWithDecision[] = []
        let from = 0
        let hasMore = true

        while (hasMore) {
          const { data, error } = await supabase
            .from("alerts")
            .select(`*, decisions (*)`)
            .order("alert_timestamp", { ascending: false })
            .range(from, from + PAGE_SIZE - 1)

          if (error) {
            console.error('Supabase fetch error:', error)
            break
          }

          if (data && data.length > 0) {
            allAlerts = allAlerts.concat(data as AlertWithDecision[])
            from += PAGE_SIZE
            hasMore = data.length === PAGE_SIZE
          } else {
            hasMore = false
          }
        }

        setAlerts(allAlerts)
        console.log(`Loaded all ${allAlerts.length} alerts from Supabase`)
      } catch (error) {
        console.error('Error loading alerts:', error)
      }
      setLoading(false)
    }
    loadAlerts()
  }, [])

  // Apply advanced filters + pair search
  const filteredAlerts = useMemo(() => {
    const alertsWithDecision = alerts.map(alert => ({
      ...alert,
      decision: alert.decisions?.[0]?.decision || undefined,
      scanner_score: alert.scanner_score
    }))
    let result = filterAlerts(alertsWithDecision, filters)
    if (pairSearch.trim()) {
      const q = pairSearch.trim().toUpperCase()
      result = result.filter(a => a.pair.toUpperCase().includes(q))
    }
    return result
  }, [alerts, filters, pairSearch])

  // Reset page when filters or search change
  useEffect(() => {
    setCurrentPage(1)
  }, [filters, pairSearch])

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
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <Bell className="w-6 h-6 text-blue-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Alerts</h1>
            <p className="text-gray-400 text-sm">
              {loading ? 'Chargement...' : `${filteredAlerts.length} / ${alerts.length} alertes`}
            </p>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Rechercher une paire..."
            value={pairSearch}
            onChange={(e) => setPairSearch(e.target.value)}
            className="pl-9 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none w-64"
          />
          {pairSearch && (
            <button
              onClick={() => setPairSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white text-xs"
            >
              x
            </button>
          )}
        </div>
      </div>

      {/* Advanced Filters */}
      <AdvancedFilters resultCount={filteredAlerts.length} showDecisions={true} />

      {/* Filtered Performance Stats */}
      <FilteredStats total={alerts.length} filtered={filteredAlerts.length} alerts={filteredAlerts} />

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">
            Chargement des alertes...
          </div>
        ) : (
          <AlertsTable alerts={paginatedAlerts as AlertWithDecision[]} onAlertClick={setSelectedAlert} />
        )}
      </div>

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between">
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
      {/* Analysis Modal */}
      {selectedAlert && (
        <AlertAnalysisModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
      )}
    </div>
  )
}
