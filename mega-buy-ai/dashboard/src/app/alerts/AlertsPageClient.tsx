'use client'

import { useState, useEffect, useMemo } from 'react'
import { Bell, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { AlertsTable } from "@/components/AlertsTable"
import { AdvancedFilters } from "@/components/AdvancedFilters"
import { FilteredStats } from "@/components/FilteredStats"
import { useAdvancedFilters } from '@/hooks/useAdvancedFilters'
import { filterAlerts } from '@/lib/filterAlerts'
import { Alert, Decision } from "@/types/database"

interface AlertWithDecision extends Alert {
  decisions?: Decision[]
}

const ITEMS_PER_PAGE = 25

export default function AlertsPageClient() {
  const [alerts, setAlerts] = useState<AlertWithDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)

  // Advanced filters
  const { filters } = useAdvancedFilters()

  // Load alerts - limit to most recent 2500 for performance
  useEffect(() => {
    const loadAlerts = async () => {
      setLoading(true)
      try {
        // First get count
        const { count } = await supabase
          .from("alerts")
          .select('*', { count: 'exact', head: true })

        // Then fetch data - limit to 2500 most recent for performance
        const { data } = await supabase
          .from("alerts")
          .select(`*, decisions (*)`)
          .order("alert_timestamp", { ascending: false })
          .limit(2500)

        setAlerts((data || []) as AlertWithDecision[])
        console.log(`Loaded ${data?.length || 0} alerts (total: ${count})`)
      } catch (error) {
        console.error('Error loading alerts:', error)
      }
      setLoading(false)
    }
    loadAlerts()
  }, [])

  // Apply advanced filters
  const filteredAlerts = useMemo(() => {
    // Map alerts to include decision from decisions array
    const alertsWithDecision = alerts.map(alert => ({
      ...alert,
      decision: alert.decisions?.[0]?.decision || undefined,
      scanner_score: alert.scanner_score
    }))
    return filterAlerts(alertsWithDecision, filters)
  }, [alerts, filters])

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
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <Bell className="w-6 h-6 text-blue-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Alerts</h1>
            <p className="text-gray-400 text-sm">
              {loading ? 'Chargement...' : `${alerts.length} alertes total`}
            </p>
          </div>
        </div>
      </div>

      {/* Advanced Filters */}
      <AdvancedFilters resultCount={filteredAlerts.length} showDecisions={true} />

      {/* Filtered Performance Stats */}
      <FilteredStats alerts={filteredAlerts} showDecisions={true} />

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">
            Chargement des alertes...
          </div>
        ) : (
          <AlertsTable alerts={paginatedAlerts as AlertWithDecision[]} />
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
    </div>
  )
}
