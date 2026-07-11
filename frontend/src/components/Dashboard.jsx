/**
 * Dashboard
 *
 * Command-center shell. 
 * DESKTOP: Three-column layout (Sidebar | Map | PriorityQueue)
 * MOBILE: Tab-based navigation between Map, Queue, and Overview
 *
 * CaseDetail slides over the map when a report is selected (not a full-page
 * modal) so the map and priority queue remain visible.
 *
 * A "Submit Report" drawer toggles the VoiceReportForm.
 */

import { useState, useCallback } from 'react'
import { useDashboardData } from '../hooks/useDashboardData'

import Sidebar       from './dashboard/Sidebar'
import ReportMap     from './dashboard/ReportMap'
import PriorityQueue from './dashboard/PriorityQueue'
import CaseDetail    from './dashboard/CaseDetail'
import VoiceReportForm from './VoiceReportForm'

export default function Dashboard() {
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
  const [mobileTab, setMobileTab] = useState('map') // 'map', 'queue', or 'overview'

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

  return (
    <div className="flex flex-col h-screen bg-gray-50 md:bg-gray-950 text-gray-900 md:text-gray-200 overflow-hidden">

      {/* ── Top bar - RESPONSIVE ── */}
      <header className="flex items-center justify-between px-3 md:px-4 py-2 md:py-3
                         bg-white md:bg-gray-900 border-b border-gray-200 md:border-gray-700/60 shrink-0 z-10 glass-panel md:glass-panel-dark">
        <div className="flex items-center gap-2 md:gap-3">
          <span className="text-base md:text-lg font-bold text-gray-900 md:text-white tracking-tight">🚨 RescueAI</span>
          <span className="text-[10px] md:text-xs text-gray-500 hidden sm:block">
            Live Disaster Response Dashboard
          </span>
        </div>

        <div className="flex items-center gap-2 md:gap-3">
          {/* Live pulse indicator */}
          <div className="flex items-center gap-1.5 text-[10px] md:text-xs text-gray-500">
            <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="hidden sm:block">
              {lastUpdated ? `Live · ${lastUpdated.toLocaleTimeString()}` : 'Connecting…'}
            </span>
          </div>

          {/* Error badge */}
          {error && (
            <span className="text-[10px] md:text-xs text-red-600 md:text-red-400 bg-red-100 md:bg-red-900/30 
                             border border-red-300 md:border-red-700/50 px-2 py-0.5 rounded">
              ⚠ {error}
            </span>
          )}

          {/* Submit report toggle - hidden on mobile */}
          <button
            onClick={() => setShowVoice(v => !v)}
            className="hidden md:block text-xs font-semibold bg-indigo-600 md:bg-indigo-700 hover:bg-indigo-700 md:hover:bg-indigo-600
                       text-white px-3 py-1.5 rounded-lg transition-colors"
          >
            {showVoice ? '✕ Close Form' : '+ Submit Report'}
          </button>
        </div>
      </header>

      {/* ── Voice intake drawer ── */}
      {showVoice && (
        <div className="shrink-0 border-b border-gray-200 md:border-gray-700/60 bg-white md:bg-gray-900 max-h-[50vh] overflow-y-auto">
          <div className="max-w-2xl mx-auto px-4 py-4">
            <VoiceReportForm onSubmitSuccess={() => { setShowVoice(false); refetch() }} />
          </div>
        </div>
      )}

      {/* ── Main layout - RESPONSIVE ── */}
      {/* DESKTOP: Three-column layout */}
      {/* MOBILE: Single view with bottom tabs */}
      <div className="flex flex-1 min-h-0">

        {/* Left: sidebar (desktop only) */}
        <div className="hidden md:block w-60 shrink-0 min-h-0">
          <Sidebar
            summary={summary}
            filters={filters}
            setFilters={setFilters}
            lastUpdated={lastUpdated}
            reportCount={reports.length}
          />
        </div>

        {/* Center: map + case detail overlay */}
        <div className={`relative flex-1 min-w-0 min-h-0 ${
          mobileTab === 'map' ? 'block' : 'hidden md:block'
        }`}>
          <ReportMap
            reports={reports}
            selectedId={selectedId}
            onSelect={handleSelect}
            loading={loading}
          />

          {/* Case detail slides over the map (or full screen on mobile) */}
          {selectedReport && (
            <div
              className="absolute top-0 right-0 h-full w-full md:w-80 z-[500]
                         shadow-2xl border-l-0 md:border-l border-gray-200 md:border-gray-700/60
                         animate-slide-in"
            >
              <CaseDetail
                report={selectedReport}
                onClose={handleClose}
                onStatusChange={handleStatusChange}
              />
            </div>
          )}
        </div>

        {/* Right: priority queue (desktop only / mobile tab) */}
        <div className={`w-full md:w-72 shrink-0 min-h-0 ${
          mobileTab === 'queue' ? 'block md:block' : 'hidden md:block'
        }`}>
          <PriorityQueue
            reports={reports}
            selectedId={selectedId}
            onSelect={handleSelect}
            loading={loading}
          />
        </div>

        {/* Mobile: Overview tab (Sidebar content) */}
        <div className={`w-full min-h-0 md:hidden ${
          mobileTab === 'overview' ? 'block' : 'hidden'
        }`}>
          <Sidebar
            summary={summary}
            filters={filters}
            setFilters={setFilters}
            lastUpdated={lastUpdated}
            reportCount={reports.length}
          />
        </div>
      </div>

      {/* ── Mobile Bottom Tab Bar ── */}
      <nav className="md:hidden flex items-center justify-around bg-white border-t border-gray-200 
                      glass-panel-dark py-2 px-2 shrink-0 safe-area-bottom">
        <button
          onClick={() => setMobileTab('map')}
          className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-all flex-1
                     ${mobileTab === 'map' 
                       ? 'bg-indigo-100 text-indigo-700' 
                       : 'text-gray-600 hover:bg-gray-100'}`}
        >
          <span className="text-xl">🗺️</span>
          <span className="text-xs font-semibold">Map</span>
        </button>
        
        <button
          onClick={() => setMobileTab('queue')}
          className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-all flex-1
                     ${mobileTab === 'queue' 
                       ? 'bg-indigo-100 text-indigo-700' 
                       : 'text-gray-600 hover:bg-gray-100'}`}
        >
          <span className="text-xl">📋</span>
          <span className="text-xs font-semibold">Queue</span>
          {reports.length > 0 && (
            <span className="absolute top-1 right-1 bg-red-500 text-white text-[9px] font-bold 
                           rounded-full w-5 h-5 flex items-center justify-center">
              {reports.length > 99 ? '99+' : reports.length}
            </span>
          )}
        </button>
        
        <button
          onClick={() => setMobileTab('overview')}
          className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-all flex-1
                     ${mobileTab === 'overview' 
                       ? 'bg-indigo-100 text-indigo-700' 
                       : 'text-gray-600 hover:bg-gray-100'}`}
        >
          <span className="text-xl">📊</span>
          <span className="text-xs font-semibold">Overview</span>
        </button>
        
        <button
          onClick={() => setShowVoice(v => !v)}
          className="flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-all flex-1
                     bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
        >
          <span className="text-xl">📱</span>
          <span className="text-xs font-semibold">Report</span>
        </button>
      </nav>
    </div>
  )
}
