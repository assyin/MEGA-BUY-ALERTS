'use client'

import { useState, useCallback, useMemo } from 'react'
import { AdvancedFilters, DEFAULT_FILTERS } from '@/types/filters'

export function useAdvancedFilters() {
  const [filters, setFiltersState] = useState<AdvancedFilters>(DEFAULT_FILTERS)

  const setFilter = useCallback(<K extends keyof AdvancedFilters>(key: K, value: AdvancedFilters[K]) => {
    setFiltersState(prev => ({ ...prev, [key]: value }))
  }, [])

  const setFilters = useCallback((newFilters: AdvancedFilters) => {
    setFiltersState(newFilters)
  }, [])

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS)
  }, [])

  const toggleArrayFilter = useCallback((key: 'timeframes' | 'conditions' | 'emotions' | 'decisions', value: string) => {
    setFiltersState(prev => {
      const arr = prev[key] || []
      const newArr = arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value]
      return { ...prev, [key]: newArr.length > 0 ? newArr : undefined }
    })
  }, [])

  const activeCount = useMemo(() => {
    let count = 0
    if (filters.dateStart) count++
    if (filters.dateEnd) count++
    if (filters.pair) count++
    if (filters.minScore !== undefined) count++
    if (filters.maxScore !== undefined) count++
    if (filters.timeframes?.length) count++
    if (filters.conditions?.length) count++
    if (filters.emotions?.length) count++
    if (filters.decisions?.length) count++
    if (filters.minDiMinus !== undefined) count++
    if (filters.maxDiPlus !== undefined) count++
    if (filters.minAdx !== undefined) count++
    if (filters.minVolPct !== undefined) count++
    if (filters.minPSuccess !== undefined) count++
    return count
  }, [filters])

  const hasActiveFilters = activeCount > 0

  return { filters, setFilter, setFilters, resetFilters, toggleArrayFilter, activeCount, hasActiveFilters }
}
