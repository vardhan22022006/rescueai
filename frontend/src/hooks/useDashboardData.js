/**
 * useDashboardData
 *
 * Central polling hook for the dashboard.  Fetches reports (every 10 s)
 * and the stats summary (every 15 s).  When USE_MOCK is true, returns
 * static mock data instead of hitting the backend.
 *
 * Returns:
 *   reports        – array, filtered + sorted by active filters
 *   summary        – stats object for stat cards
 *   filters        – current filter state
 *   setFilters     – update filters
 *   selectedId     – currently selected report id
 *   setSelectedId  – select a report (opens detail panel)
 *   loading        – true on first fetch
 *   error          – fetch error string or null
 *   lastUpdated    – Date of last successful fetch
 *   refetch        – manually trigger a refresh
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { USE_MOCK, MOCK_REPORTS, MOCK_SUMMARY } from '../data/mockData'

const REPORTS_POLL_MS  = 10_000   // 10 s
const SUMMARY_POLL_MS  = 15_000   // 15 s

export const DEFAULT_FILTERS = {
  disasterType:       'all',   // 'all' | 'flood' | 'earthquake' | 'cyclone' | 'other'
  verificationStatus: 'all',   // 'all' | 'unverified' | 'corroborated' | 'satellite_confirmed' | 'weather_confirmed'
  minUrgency:         0,       // 0–100
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function applyFilters(reports, filters) {
  return reports
    .filter(r => {
      if (filters.disasterType !== 'all' && r.disaster_type !== filters.disasterType) return false
      if (filters.verificationStatus !== 'all' && r.verification_status !== filters.verificationStatus) return false
      const score = r.urgency?.score ?? r.urgency_score ?? 0
      if (score < filters.minUrgency) return false
      return true
    })
    .sort((a, b) => {
      const sa = a.urgency?.score ?? a.urgency_score ?? 0
      const sb = b.urgency?.score ?? b.urgency_score ?? 0
      return sb - sa
    })
}

async function fetchReports() {
  const res = await fetch('/api/reports?limit=100')
  if (!res.ok) throw new Error(`/api/reports responded ${res.status}`)
  const data = await res.json()
  // Normalise: real API wraps in { reports: [...] }
  return Array.isArray(data) ? data : (data.reports ?? [])
}

async function fetchSummary() {
  const res = await fetch('/api/stats/summary')
  if (!res.ok) throw new Error(`/api/stats/summary responded ${res.status}`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useDashboardData() {
  const [allReports,   setAllReports]   = useState([])
  const [summary,      setSummary]      = useState(null)
  const [filters,      setFilters]      = useState(DEFAULT_FILTERS)
  const [selectedId,   setSelectedId]   = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState(null)
  const [lastUpdated,  setLastUpdated]  = useState(null)

  const reportsTimerRef = useRef(null)
  const summaryTimerRef = useRef(null)

  // ── fetch reports ─────────────────────────────────────────────────────
  const loadReports = useCallback(async (isInitial = false) => {
    if (USE_MOCK) {
      setAllReports(MOCK_REPORTS)
      if (isInitial) setLoading(false)
      setLastUpdated(new Date())
      return
    }
    try {
      const data = await fetchReports()
      setAllReports(data)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      if (isInitial) setLoading(false)
    }
  }, [])

  // ── fetch summary ─────────────────────────────────────────────────────
  const loadSummary = useCallback(async () => {
    if (USE_MOCK) {
      setSummary(MOCK_SUMMARY)
      return
    }
    try {
      const data = await fetchSummary()
      setSummary(data)
    } catch {
      // summary is non-critical — silently ignore
    }
  }, [])

  // ── initial load + polling setup ──────────────────────────────────────
  useEffect(() => {
    loadReports(true)
    loadSummary()

    reportsTimerRef.current = setInterval(() => loadReports(false), REPORTS_POLL_MS)
    summaryTimerRef.current = setInterval(loadSummary, SUMMARY_POLL_MS)

    return () => {
      clearInterval(reportsTimerRef.current)
      clearInterval(summaryTimerRef.current)
    }
  }, [loadReports, loadSummary])

  // ── public refetch ────────────────────────────────────────────────────
  const refetch = useCallback(() => {
    loadReports(false)
    loadSummary()
  }, [loadReports, loadSummary])

  // ── apply client-side filters ─────────────────────────────────────────
  const reports = applyFilters(allReports, filters)

  return {
    reports,
    allReports,
    summary,
    filters,
    setFilters,
    selectedId,
    setSelectedId,
    loading,
    error,
    lastUpdated,
    refetch,
  }
}
