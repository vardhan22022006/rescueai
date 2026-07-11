/**
 * CaseDetail
 *
 * Slide-in panel (right side overlay on map) showing full report detail:
 *  - Header: disaster type, urgency score, status, time
 *  - Report text (original + translated)
 *  - Urgency score breakdown as a horizontal bar chart
 *  - Verification status + corroboration count
 *  - Dispatch recommendations (fetched on open)
 *  - Action buttons: Assign Team, In Progress, Resolved, False Report
 * 
 * RESPONSIVE: Full-screen on mobile with close button, sidebar overlay on desktop
 */

import { useState, useEffect, useCallback } from 'react'
import { USE_MOCK, MOCK_DISPATCH } from '../../data/mockData'
import {
  DISASTER_ICONS,
  VERIFICATION_ICONS,
  VULNERABLE_COLORS,
  urgencyColor,
  timeAgo,
} from './PriorityQueue'

// ---------------------------------------------------------------------------
// Urgency bar chart
// ---------------------------------------------------------------------------
const FACTOR_META = {
  people:        { label: 'People Affected',    color: 'bg-blue-500',   max: 30 },
  vulnerable:    { label: 'Vulnerable Groups',  color: 'bg-pink-500',   max: 45 },
  verification:  { label: 'Verification',       color: 'bg-green-500',  max: 25 },
  corroboration: { label: 'Corroboration',      color: 'bg-indigo-500', max: 20 },
  time_decay:    { label: 'Time Without Update',color: 'bg-amber-500',  max: 20 },
}

function UrgencyBreakdown({ breakdown }) {
  if (!breakdown?.factors) return null
  const { factors, multiplier, final_score, base_score } = breakdown

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Urgency Breakdown
        </h3>
        <span className={`text-sm font-bold px-2 py-0.5 rounded-full tabular-nums ${urgencyColor(final_score)}`}>
          {Math.round(final_score)} / 100
        </span>
      </div>

      <div className="space-y-2">
        {Object.entries(FACTOR_META).map(([key, meta]) => {
          const factor = factors[key]
          if (!factor) return null
          const pct = Math.min(100, Math.round((factor.score / meta.max) * 100))
          return (
            <div key={key}>
              <div className="flex justify-between text-xs text-gray-400 mb-0.5">
                <span>{meta.label}</span>
                <span className="tabular-nums text-gray-300 font-medium">
                  {factor.score} / {meta.max}
                </span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${meta.color}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="text-[10px] text-gray-600 mt-0.5">{factor.explanation}</p>
            </div>
          )
        })}
      </div>

      {multiplier && (
        <div className="mt-2 pt-2 border-t border-gray-700 flex justify-between text-xs text-gray-400">
          <span>Disaster multiplier</span>
          <span className="text-gray-300 font-medium">× {multiplier.value}</span>
        </div>
      )}
      {breakdown.summary && (
        <p className="mt-2 text-xs text-gray-500 italic">{breakdown.summary}</p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dispatch recommendations
// ---------------------------------------------------------------------------
const TEAM_TYPE_COLORS = {
  NDRF:      'text-red-400',
  SDRF:      'text-orange-400',
  NGO:       'text-green-400',
  volunteer: 'text-blue-400',
}

function DispatchRecs({ reportId, reportLat, reportLon, onAssign }) {
  const [recs,       setRecs]       = useState(null)
  const [loadingRec, setLoadingRec] = useState(true)
  const [recError,   setRecError]   = useState(null)

  useEffect(() => {
    if (!reportId) return
    setLoadingRec(true)
    setRecError(null)

    if (USE_MOCK) {
      setTimeout(() => {
        setRecs(MOCK_DISPATCH[reportId]?.recommendations ?? [])
        setLoadingRec(false)
      }, 300)
      return
    }

    if (!reportLat || !reportLon) {
      setRecs([])
      setLoadingRec(false)
      return
    }

    fetch(`/api/reports/${reportId}/recommend-dispatch`)
      .then(r => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.json()
      })
      .then(data => {
        setRecs(data.recommendations ?? [])
        setLoadingRec(false)
      })
      .catch(err => {
        setRecError(err.message)
        setLoadingRec(false)
      })
  }, [reportId, reportLat, reportLon])

  if (loadingRec) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 py-2">
        <div className="w-4 h-4 border-2 border-gray-600 border-t-indigo-500 rounded-full animate-spin" />
        Loading teams…
      </div>
    )
  }

  if (recError) {
    return <p className="text-xs text-red-400">Could not load teams: {recError}</p>
  }

  if (!recs || recs.length === 0) {
    return (
      <p className="text-xs text-gray-500">
        {reportLat ? 'No available teams nearby.' : 'No GPS coordinates — cannot recommend teams.'}
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {recs.map(team => (
        <div
          key={team.team_id}
          className="flex items-center justify-between bg-gray-800/60 rounded-lg px-3 py-2
                     border border-gray-700/50"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-200 truncate">{team.team_name}</p>
            <p className="text-xs text-gray-500">
              <span className={`font-semibold ${TEAM_TYPE_COLORS[team.team_type] ?? 'text-gray-400'}`}>
                {team.team_type}
              </span>
              {' · '}Cap {team.capacity}
              {' · '}
              <span className="text-gray-400">{team.distance_km} km · {team.eta_estimate}</span>
            </p>
          </div>
          <button
            onClick={() => onAssign(team.team_id, team.team_name)}
            className="ml-3 shrink-0 text-xs bg-indigo-700 hover:bg-indigo-600
                       text-white font-semibold px-3 py-2 rounded-lg transition-colors"
            style={{ minHeight: '44px', minWidth: '70px' }}
          >
            Assign
          </button>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status action buttons
// ---------------------------------------------------------------------------
const STATUS_ACTIONS = [
  { value: 'in_progress',  label: '▶ In Progress', cls: 'bg-amber-700 hover:bg-amber-600 text-white'  },
  { value: 'resolved',     label: '✔ Resolved',    cls: 'bg-green-700 hover:bg-green-600 text-white'  },
  { value: 'false_report', label: '✕ False Report', cls: 'bg-gray-700  hover:bg-gray-600  text-gray-300' },
]

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function CaseDetail({ report, onClose, onStatusChange, onViewFull }) {
  const [actionState, setActionState] = useState({}) // { [status]: 'loading'|'done'|'error' }
  const [assignState, setAssignState] = useState(null) // null | 'loading' | { teamName } | 'error'

  // Reset action state when report changes
  useEffect(() => {
    setActionState({})
    setAssignState(null)
  }, [report?.id])

  const handleStatusChange = useCallback(async (newStatus) => {
    if (USE_MOCK) {
      setActionState(prev => ({ ...prev, [newStatus]: 'done' }))
      onStatusChange?.(report.id, newStatus)
      return
    }
    setActionState(prev => ({ ...prev, [newStatus]: 'loading' }))
    try {
      const res = await fetch(`/api/reports/${report.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setActionState(prev => ({ ...prev, [newStatus]: 'done' }))
      onStatusChange?.(report.id, newStatus)
    } catch {
      setActionState(prev => ({ ...prev, [newStatus]: 'error' }))
    }
  }, [report?.id, onStatusChange])

  const handleAssign = useCallback(async (teamId, teamName) => {
    if (USE_MOCK) {
      setAssignState({ teamName })
      onStatusChange?.(report.id, 'in_progress')
      return
    }
    setAssignState('loading')
    try {
      const res = await fetch(`/api/reports/${report.id}/assign?team_id=${teamId}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setAssignState({ teamName })
      onStatusChange?.(report.id, 'in_progress')
    } catch {
      setAssignState('error')
    }
  }, [report?.id, onStatusChange])

  if (!report) return null

  const score         = report.urgency?.score ?? report.urgency_score ?? 0
  const breakdown     = report.urgency?.breakdown ?? report.urgency_breakdown
  const vInfo         = VERIFICATION_ICONS[report.verification_status] ?? VERIFICATION_ICONS.unverified
  const flags         = report.vulnerable_flags ?? []
  const locText       = report.location?.text ?? report.location?.location_text

  return (
    <div className="flex flex-col h-full bg-gray-900 md:border-l border-gray-700/60 overflow-hidden">
      {/* ── Header - RESPONSIVE ── */}
      <div className="flex items-start justify-between px-3 md:px-4 pt-3 md:pt-4 pb-2 md:pb-3
                      border-b border-gray-700/60 shrink-0">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xl md:text-xl leading-none">
              {DISASTER_ICONS[report.disaster_type] ?? '⚠️'}
            </span>
            <h2 className="text-base md:text-base font-bold text-white capitalize">
              {report.disaster_type} Report
            </h2>
            <span className={`text-xs md:text-xs font-bold px-2 py-1 rounded-full tabular-nums ${urgencyColor(score)}`}>
              {Math.round(score)}
            </span>
          </div>
          <p className="text-xs md:text-xs text-gray-500 leading-relaxed">
            {timeAgo(report.created_at)}
            {locText && <> · {locText}</>}
            {' · '}
            <span className="uppercase tracking-wide">{report.source}</span>
          </p>
          {onViewFull && (
            <button
              onClick={onViewFull}
              className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 underline"
            >
              View Full Detail →
            </button>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Close detail panel"
          className="ml-3 text-gray-500 hover:text-white transition-colors text-2xl md:text-xl 
                     leading-none shrink-0 w-10 h-10 md:w-auto md:h-auto flex items-center justify-center
                     md:block active:bg-gray-800 md:active:bg-transparent rounded-lg"
          style={{ minWidth: '44px', minHeight: '44px' }}
        >
          ✕
        </button>
      </div>

      {/* ── Scrollable body - RESPONSIVE ── */}
      <div className="flex-1 overflow-y-auto px-3 md:px-4 py-3 md:py-4 space-y-4 md:space-y-5">

        {/* Verification + corroboration - RESPONSIVE */}
        <div className="flex items-center gap-2 md:gap-3 flex-wrap">
          <span className={`flex items-center gap-1 text-sm md:text-sm font-medium ${vInfo.color}`}>
            {vInfo.icon} {vInfo.label}
          </span>
          {report.corroboration_count > 0 && (
            <span className="text-xs md:text-xs bg-indigo-900/50 text-indigo-400 border border-indigo-700/50
                             px-2 py-0.5 rounded-full">
              {report.corroboration_count} corroborating
            </span>
          )}
          {flags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {flags.map(f => (
                <span
                  key={f}
                  className={`text-xs md:text-xs px-2 py-0.5 rounded border capitalize font-medium
                              ${VULNERABLE_COLORS[f] ?? 'bg-gray-800 text-gray-400 border-gray-700'}`}
                >
                  {f}
                </span>
              ))}
            </div>
          )}
          {report.num_people != null && (
            <span className="text-xs md:text-xs text-gray-400">👤 {report.num_people} people</span>
          )}
        </div>

        {/* Report text - RESPONSIVE */}
        <Section title="Report Text">
          <p className="text-sm md:text-sm text-gray-300 leading-relaxed bg-gray-800/50 rounded-lg p-3
                        border border-gray-700/40 whitespace-pre-wrap">
            {report.raw_text}
          </p>
          {report.translated_text && report.translated_text !== report.raw_text && (
            <>
              <p className="text-[10px] md:text-[10px] text-gray-600 uppercase tracking-wide mt-2 mb-1">
                Translated from {report.language}
              </p>
              <p className="text-sm md:text-sm text-gray-400 leading-relaxed bg-gray-800/30 rounded-lg p-3
                            border border-gray-700/30 italic whitespace-pre-wrap">
                {report.translated_text}
              </p>
            </>
          )}
        </Section>

        {/* Urgency breakdown - RESPONSIVE */}
        {breakdown && (
          <Section title="">
            <UrgencyBreakdown breakdown={breakdown} />
          </Section>
        )}

        {/* Dispatch recommendations - RESPONSIVE */}
        <Section title="Nearest Available Teams">
          <DispatchRecs
            reportId={report.id}
            reportLat={report.location?.latitude}
            reportLon={report.location?.longitude}
            onAssign={handleAssign}
          />
          {assignState === 'loading' && (
            <p className="text-xs text-gray-500 mt-2">Assigning team…</p>
          )}
          {assignState?.teamName && (
            <p className="text-xs text-green-400 mt-2">
              ✓ Assigned to {assignState.teamName}
            </p>
          )}
          {assignState === 'error' && (
            <p className="text-xs text-red-400 mt-2">Assignment failed. Try again.</p>
          )}
        </Section>

        {/* Status actions - RESPONSIVE: Stack on very narrow screens */}
        <Section title="Update Status">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {STATUS_ACTIONS.map(({ value, label, cls }) => {
              const state = actionState[value]
              return (
                <button
                  key={value}
                  onClick={() => handleStatusChange(value)}
                  disabled={state === 'loading' || state === 'done' || report.status === value}
                  className={`text-xs md:text-xs font-semibold px-3 py-2 md:py-1.5 rounded-lg transition-colors
                              disabled:opacity-40 disabled:cursor-not-allowed ${cls}`}
                  style={{ minHeight: '44px' }}
                >
                  {state === 'loading' ? '…' : state === 'done' ? '✓ Done' : label}
                </button>
              )
            })}
          </div>
          {Object.values(actionState).includes('error') && (
            <p className="text-xs text-red-400 mt-1">Status update failed.</p>
          )}
        </Section>

        {/* Report meta - RESPONSIVE */}
        <Section title="Report Info">
          <dl className="grid grid-cols-2 gap-x-3 md:gap-x-4 gap-y-1 text-xs md:text-xs">
            <MetaRow label="ID"       value={report.id.slice(0, 8) + '…'} />
            <MetaRow label="Source"   value={report.source?.toUpperCase()} />
            <MetaRow label="Language" value={report.language?.toUpperCase() ?? 'EN'} />
            <MetaRow label="Status"   value={report.status?.replace('_', ' ')} />
            {report.assigned_team && (
              <MetaRow label="Assigned" value={report.assigned_team} />
            )}
            {report.location?.latitude && (
              <MetaRow
                label="GPS"
                value={`${report.location.latitude.toFixed(4)}, ${report.location.longitude.toFixed(4)}`}
              />
            )}
          </dl>
        </Section>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Small layout helpers
// ---------------------------------------------------------------------------
function Section({ title, children }) {
  return (
    <div>
      {title && (
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">
          {title}
        </h3>
      )}
      {children}
    </div>
  )
}

function MetaRow({ label, value }) {
  return (
    <>
      <dt className="text-gray-600">{label}</dt>
      <dd className="text-gray-300 font-medium truncate">{value ?? '—'}</dd>
    </>
  )
}
