/**
 * CommandCenter — Screen 2
 *
 * The existing Dashboard component, but wrapped with navigation.
 * Keeps all existing functionality (map, filters, priority queue, case detail).
 */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboardData } from '../hooks/useDashboardData'

import Sidebar       from './dashboard/Sidebar'
import ReportMap     from './dashboard/ReportMap'
import PriorityQueue from './dashboard/PriorityQueue'
import CaseDetail    from './dashboard/CaseDetail'
import VoiceReportForm from './VoiceReportForm'
import Navigation from './Navigation'

export default function CommandCenter() {
  const navigate = useNavigate()
  const {
    reports,
    summary,
    filters,
    setFilters,
    selectedId,
    setSelectedId,
    loading,
    error,
    lastUpdated,
    refetch,
  } = useDashboardData()

  const [showVoice, setShowVoice] = useState(false)

  const selectedReport = selectedId
    ? reports.find(r => r.id === selectedId) ?? null
    : null

  const handleSelect = useCallback((id) => {
    setSelectedId(prev => (prev === id ? null : id))
  }, [setSelectedId])

  const handleClose = useCallback(() => setSelectedId(null), [setSelectedId])

  const handleStatusChange = useCallback(() => {
    refetch()
  }, [refetch])

  // When a report card is clicked, navigate to full incident detail view
  const handleViewIncident = useCallback((id) => {
    navigate(`/incident/${id}`)
  }, [navigate])

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-200 overflow-hidden">
      {/* Top Navigation */}
      <Navigation />

      {/* ── Top bar ── */}
      <header className="flex items-center justify-between px-4 py-2
                         bg-gray-900 border-b border-gray-700/60 shrink-0 z-10">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-white tracking-tight">Command Center</span>
          <span className="text-xs text-gray-500 hidden sm:block">
            Live disaster response dashboard
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Live pulse indicator */}
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="hidden sm:block">
              {lastUpdated ? `Live · ${lastUpdated.toLocaleTimeString()}` : 'Connecting…'}
            </span>
          </div>

          {/* Error badge */}
          {error && (
            <span className="text-xs text-red-400 bg-red-900/30 border border-red-700/50
                             px-2 py-0.5 rounded">
              ⚠ {error}
            </span>
          )}

          {/* Submit report toggle */}
          <button
            onClick={() => setShowVoice(v => !v)}
            className="text-xs font-semibold bg-indigo-700 hover:bg-indigo-600
                       text-white px-3 py-1.5 rounded-lg transition-colors"
          >
            {showVoice ? '✕ Close Form' : '+ Submit Report'}
          </button>
        </div>
      </header>

      {/* ── Voice intake drawer ── */}
      {showVoice && (
        <div className="shrink-0 border-b border-gray-700/60 bg-gray-900 max-h-[50vh] overflow-y-auto">
          <div className="max-w-2xl mx-auto px-4 py-4">
            <VoiceReportForm onSubmitSuccess={() => { setShowVoice(false); refetch() }} />
          </div>
        </div>
      )}

      {/* ── Main three-column layout ── */}
      <div className="flex flex-1 min-h-0">

        {/* Left: sidebar (filters + stats) */}
        <div className="w-60 shrink-0 min-h-0">
          <Sidebar
            summary={summary}
            filters={filters}
            setFilters={setFilters}
            lastUpdated={lastUpdated}
            reportCount={reports.length}
          />
        </div>

        {/* Center: map + case detail overlay */}
        <div className="relative flex-1 min-w-0 min-h-0">
          <ReportMap
            reports={reports}
            selectedId={selectedId}
            onSelect={handleSelect}
            loading={loading}
          />

          {/* Case detail slides over the right portion of the map */}
          {selectedReport && (
            <div
              className="absolute top-0 right-0 h-full w-80 z-[500]
                         shadow-2xl border-l border-gray-700/60
                         animate-slide-in"
            >
              <CaseDetail
                report={selectedReport}
                onClose={handleClose}
                onStatusChange={handleStatusChange}
                onViewFull={() => handleViewIncident(selectedReport.id)}
              />
            </div>
          )}
        </div>

        {/* Right: priority queue */}
        <div className="w-72 shrink-0 min-h-0">
          <PriorityQueue
            reports={reports}
            selectedId={selectedId}
            onSelect={handleSelect}
            loading={loading}
          />
        </div>
      </div>
    </div>
  )
}
