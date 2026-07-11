/**
 * Sidebar
 *
 * Left column of the dashboard:
 * - Stat cards (active reports, critical, teams available, unverified)
 * - Filter controls: disaster type, verification status, min-urgency slider
 * - Mock-data indicator badge
 * 
 * RESPONSIVE: Collapsible filters on mobile for better space utilization
 */

import { useState } from 'react'
import { DEFAULT_FILTERS } from '../../hooks/useDashboardData'
import { USE_MOCK } from '../../data/mockData'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const DISASTER_TYPES = [
  { value: 'all',        label: 'All Types' },
  { value: 'flood',      label: '🌊 Flood' },
  { value: 'earthquake', label: '🌍 Earthquake' },
  { value: 'cyclone',    label: '🌀 Cyclone' },
  { value: 'other',      label: '⚠️ Other' },
]

const VERIFICATION_STATUSES = [
  { value: 'all',                  label: 'All Statuses' },
  { value: 'unverified',           label: '❓ Unverified' },
  { value: 'corroborated',         label: '👥 Corroborated' },
  { value: 'weather_confirmed',    label: '🌦️ Weather Confirmed' },
  { value: 'satellite_confirmed',  label: '🛰️ Satellite Confirmed' },
]

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function StatCard({ label, value, highlight = false, sub }) {
  return (
    <div className={`glass-panel rounded-lg p-3 md:p-4 border ${
      highlight
        ? 'bg-red-50 border-red-200'
        : 'border-gray-200'
    }`}>
      <p className="text-[10px] md:text-xs font-medium text-gray-600 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl md:text-3xl font-bold tabular-nums ${highlight ? 'text-red-600' : 'text-gray-900'}`}>
        {value ?? '—'}
      </p>
      {sub && <p className="text-[10px] md:text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <p className="text-xs font-semibold text-gray-700 uppercase tracking-widest mb-2 mt-4 md:mt-5">
      {children}
    </p>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function Sidebar({ summary, filters, setFilters, lastUpdated, reportCount }) {
  const r = summary?.reports
  const t = summary?.teams
  const [filtersExpanded, setFiltersExpanded] = useState(false)

  function update(key, value) {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  function resetFilters() {
    setFilters(DEFAULT_FILTERS)
  }

  const filtersActive =
    filters.disasterType !== 'all' ||
    filters.verificationStatus !== 'all' ||
    filters.minUrgency > 0

  return (
    <aside className="flex flex-col h-full bg-gray-50 border-r border-gray-200 overflow-y-auto">
      {/* ── Header - RESPONSIVE ── */}
      <div className="px-3 md:px-4 pt-3 md:pt-4 pb-2 md:pb-3 border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-base md:text-lg font-bold text-gray-900 tracking-tight">📊 Overview</span>
          {USE_MOCK && (
            <span className="text-[9px] md:text-[10px] font-semibold bg-amber-500/20 text-amber-700
                             border border-amber-500/40 px-1.5 py-0.5 rounded uppercase tracking-wide">
              Mock
            </span>
          )}
        </div>
        <p className="text-[10px] md:text-[11px] text-gray-500">
          {lastUpdated
            ? `Updated ${lastUpdated.toLocaleTimeString()}`
            : 'Connecting…'}
        </p>
      </div>

      <div className="px-3 md:px-4 py-2 md:py-3 flex-1">
        {/* ── Stat cards - RESPONSIVE ── */}
        <SectionLabel>System Status</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          <StatCard
            label="Active"
            value={r?.active ?? reportCount}
            sub="open reports"
          />
          <StatCard
            label="Critical"
            value={r?.critical}
            highlight
            sub="score ≥ 80"
          />
          <StatCard
            label="Teams Free"
            value={t?.available}
            sub={t ? `of ${t.total} total` : undefined}
          />
          <StatCard
            label="Unverified"
            value={r?.unverified}
            sub="need attention"
          />
        </div>

        {/* ── Filters Section - COLLAPSIBLE ON MOBILE ── */}
        <div className="mt-4 md:mt-5">
          {/* Filter Header with Expand/Collapse button */}
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setFiltersExpanded(!filtersExpanded)}
              className="flex items-center gap-2 md:pointer-events-none w-full md:w-auto"
            >
              <SectionLabel>Filters</SectionLabel>
              <span className="md:hidden text-gray-500 text-lg">
                {filtersExpanded ? '▼' : '▶'}
              </span>
            </button>
            {filtersActive && (
              <button
                onClick={resetFilters}
                className="text-[10px] md:text-[11px] text-indigo-600 hover:text-indigo-700 underline
                           font-semibold px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
              >
                Reset
              </button>
            )}
          </div>

          {/* Filters Content - Hidden by default on mobile, always visible on desktop */}
          <div className={`space-y-3 ${filtersExpanded ? 'block' : 'hidden'} md:block`}>
            {/* Disaster type */}
            <div>
              <label className="block text-xs text-gray-600 mb-1 font-medium">Disaster Type</label>
              <select
                value={filters.disasterType}
                onChange={e => update('disasterType', e.target.value)}
                className="w-full glass-panel border border-gray-300 text-gray-900 text-sm
                           rounded-md px-2 py-2 md:py-1.5
                           focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{ minHeight: '44px' }}
              >
                {DISASTER_TYPES.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Verification status */}
            <div>
              <label className="block text-xs text-gray-600 mb-1 font-medium">Verification Status</label>
              <select
                value={filters.verificationStatus}
                onChange={e => update('verificationStatus', e.target.value)}
                className="w-full glass-panel border border-gray-300 text-gray-900 text-sm
                           rounded-md px-2 py-2 md:py-1.5
                           focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{ minHeight: '44px' }}
              >
                {VERIFICATION_STATUSES.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {/* Min urgency slider */}
            <div>
              <label className="block text-xs text-gray-600 mb-1 font-medium">
                Min Urgency Score
                <span className="ml-2 text-indigo-600 font-semibold tabular-nums">
                  {filters.minUrgency}
                </span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={filters.minUrgency}
                onChange={e => update('minUrgency', Number(e.target.value))}
                className="w-full accent-indigo-500 mb-1"
                style={{ minHeight: '44px' }}
              />
              <div className="flex justify-between text-[10px] text-gray-500">
                <span>0 — Low</span>
                <span>50 — Med</span>
                <span>100 — Critical</span>
              </div>
            </div>
          </div>
        </div>

        {/* Filtered count - RESPONSIVE */}
        <div className="mt-4 md:mt-3 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
          <p className="text-xs text-gray-700 text-center">
            Showing <span className="text-indigo-700 font-bold text-sm">{reportCount}</span> report{reportCount !== 1 ? 's' : ''}
            {filtersActive && ' (filtered)'}
          </p>
        </div>
      </div>
    </aside>
  )
}
