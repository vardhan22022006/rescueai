/**
 * IncidentDetail — Screen 3 (dynamic)
 *
 * Full-page view of a single incident with expanded AI reasoning.
 * ALL data must come from the real backend API — no fabrication.
 */

import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { USE_MOCK, MOCK_REPORTS, MOCK_DISPATCH } from '../data/mockData'
import Navigation from './Navigation'
import {
  DISASTER_ICONS,
  VERIFICATION_ICONS,
  VULNERABLE_COLORS,
  urgencyColor,
  timeAgo,
} from './dashboard/PriorityQueue'

// Reuse the urgency breakdown component logic
const FACTOR_META = {
  people:        { label: 'People Affected',    color: 'bg-blue-500',   max: 30 },
  vulnerable:    { label: 'Vulnerable Groups',  color: 'bg-pink-500',   max: 45 },
  verification:  { label: 'Verification',       color: 'bg-green-500',  max: 25 },
  corroboration: { label: 'Corroboration',      color: 'bg-indigo-500', max: 20 },
  time_decay:    { label: 'Time Without Update',color: 'bg-amber-500',  max: 20 },
}

const TEAM_TYPE_COLORS = {
  NDRF:      'text-red-400',
  SDRF:      'text-orange-400',
  NGO:       'text-green-400',
  volunteer: 'text-blue-400',
}

export default function IncidentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  
  const [report, setReport] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionState, setActionState] = useState({})
  const [assignState, setAssignState] = useState(null)

  useEffect(() => {
    async function loadReport() {
      if (USE_MOCK) {
        const mockReport = MOCK_REPORTS.find(r => r.id === id)
        if (!mockReport) {
          setError('Report not found')
          setLoading(false)
          return
        }
        setReport(mockReport)
        setRecommendations(MOCK_DISPATCH[id]?.recommendations ?? [])
        setLoading(false)
        return
      }

      try {
        const res = await fetch(`/api/reports/${id}`)
        if (!res.ok) throw new Error(`Report ${id} not found`)
        const data = await res.json()
        setReport(data)

        // Load dispatch recommendations
        if (data.location?.latitude && data.location?.longitude) {
          const recRes = await fetch(`/api/reports/${id}/recommend-dispatch`)
          if (recRes.ok) {
            const recData = await recRes.json()
            setRecommendations(recData.recommendations ?? [])
          }
        }

        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadReport()
  }, [id])

  const handleStatusChange = useCallback(async (newStatus) => {
    if (USE_MOCK) {
      setActionState(prev => ({ ...prev, [newStatus]: 'done' }))
      return
    }
    setActionState(prev => ({ ...prev, [newStatus]: 'loading' }))
    try {
      const res = await fetch(`/api/reports/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setActionState(prev => ({ ...prev, [newStatus]: 'done' }))
      // Reload report to get updated data
      const updatedRes = await fetch(`/api/reports/${id}`)
      if (updatedRes.ok) {
        const updatedData = await updatedRes.json()
        setReport(updatedData)
      }
    } catch {
      setActionState(prev => ({ ...prev, [newStatus]: 'error' }))
    }
  }, [id])

  const handleAssign = useCallback(async (teamId, teamName) => {
    if (USE_MOCK) {
      setAssignState({ teamName })
      return
    }
    setAssignState('loading')
    try {
      const res = await fetch(`/api/reports/${id}/assign?team_id=${teamId}`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setAssignState({ teamName })
      // Reload report
      const updatedRes = await fetch(`/api/reports/${id}`)
      if (updatedRes.ok) {
        const updatedData = await updatedRes.json()
        setReport(updatedData)
      }
    } catch {
      setAssignState('error')
    }
  }, [id])

  if (loading) {
    return (
      <div className="flex flex-col h-screen bg-gray-950 text-gray-200">
        <Navigation />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-gray-600 border-t-indigo-500 rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="flex flex-col h-screen bg-gray-950 text-gray-200">
        <Navigation />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-400 text-lg mb-2">⚠️ {error || 'Report not found'}</p>
            <button
              onClick={() => navigate('/command-center')}
              className="text-sm text-indigo-400 hover:text-indigo-300 underline"
            >
              Return to Command Center
            </button>
          </div>
        </div>
      </div>
    )
  }

  const score = report.urgency?.score ?? report.urgency_score ?? 0
  const breakdown = report.urgency?.breakdown ?? report.urgency_breakdown
  const vInfo = VERIFICATION_ICONS[report.verification_status] ?? VERIFICATION_ICONS.unverified
  const flags = report.vulnerable_flags ?? []
  const locText = report.location?.text ?? report.location?.location_text

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-200">
      <Navigation />
      
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => navigate('/command-center')}
              className="text-sm text-gray-500 hover:text-white mb-3 inline-flex items-center gap-1"
            >
              ← Back to Command Center
            </button>
            
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-4xl">
                    {DISASTER_ICONS[report.disaster_type] ?? '⚠️'}
                  </span>
                  <div>
                    <h1 className="text-3xl font-bold text-white capitalize">
                      {report.disaster_type} Incident
                    </h1>
                    <p className="text-sm text-gray-500">
                      Report ID: {report.id}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3 mt-3">
                  <span className={`text-lg font-bold px-3 py-1 rounded-full tabular-nums ${urgencyColor(score)}`}>
                    Urgency: {Math.round(score)} / 100
                  </span>
                  <span className={`flex items-center gap-1.5 text-sm font-medium ${vInfo.color}`}>
                    {vInfo.icon} {vInfo.label}
                  </span>
                  <span className="text-sm text-gray-500">
                    {timeAgo(report.created_at)}
                    {locText && <> · {locText}</>}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Two-column layout */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main content - 2 columns */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Report Text */}
              <Section title="Report Details">
                <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-6">
                  <div className="flex flex-wrap gap-3 mb-4">
                    {flags.map(f => (
                      <span
                        key={f}
                        className={`text-sm px-3 py-1 rounded-lg border capitalize font-medium
                                    ${VULNERABLE_COLORS[f] ?? 'bg-gray-800 text-gray-400 border-gray-700'}`}
                      >
                        {f}
                      </span>
                    ))}
                    {report.num_people != null && (
                      <span className="text-sm bg-blue-900/50 text-blue-300 border border-blue-700/50 px-3 py-1 rounded-lg">
                        👤 {report.num_people} people affected
                      </span>
                    )}
                  </div>
                  
                  <p className="text-gray-300 leading-relaxed whitespace-pre-wrap mb-3">
                    {report.raw_text}
                  </p>
                  
                  {report.translated_text && report.translated_text !== report.raw_text && (
                    <>
                      <p className="text-xs text-gray-600 uppercase tracking-wide mb-2">
                        Translated from {report.language}
                      </p>
                      <p className="text-sm text-gray-400 leading-relaxed italic whitespace-pre-wrap">
                        {report.translated_text}
                      </p>
                    </>
                  )}
                  
                  <div className="mt-4 pt-4 border-t border-gray-700 flex flex-wrap gap-4 text-xs text-gray-500">
                    <span>Source: <span className="text-gray-300 uppercase">{report.source}</span></span>
                    <span>Language: <span className="text-gray-300 uppercase">{report.language ?? 'EN'}</span></span>
                    <span>Status: <span className="text-gray-300 capitalize">{report.status?.replace('_', ' ')}</span></span>
                  </div>
                </div>
              </Section>

              {/* AI Reasoning */}
              <Section title="AI Reasoning & Urgency Breakdown">
                <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-6">
                  {breakdown?.factors ? (
                    <>
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-400 mb-3">
                          How the AI calculated urgency score {Math.round(score)}/100:
                        </h4>
                        <ul className="space-y-2 text-sm text-gray-300">
                          {Object.entries(FACTOR_META).map(([key, meta]) => {
                            const factor = breakdown.factors[key]
                            if (!factor || factor.score === 0) return null
                            return (
                              <li key={key} className="flex items-start gap-2">
                                <span className="text-green-400 mt-0.5">✓</span>
                                <span>
                                  <strong className={meta.color.replace('bg-', 'text-').replace('-500', '-400')}>
                                    {meta.label}:
                                  </strong>
                                  {' '}+{factor.score} points — {factor.explanation}
                                </span>
                              </li>
                            )
                          })}
                          {breakdown.multiplier && breakdown.multiplier.value !== 1.0 && (
                            <li className="flex items-start gap-2">
                              <span className="text-amber-400 mt-0.5">✦</span>
                              <span>
                                <strong className="text-amber-400">Disaster Multiplier:</strong>
                                {' '}×{breakdown.multiplier.value} — {breakdown.multiplier.explanation}
                              </span>
                            </li>
                          )}
                        </ul>
                      </div>

                      <div className="space-y-2">
                        {Object.entries(FACTOR_META).map(([key, meta]) => {
                          const factor = breakdown.factors[key]
                          if (!factor) return null
                          const pct = Math.min(100, Math.round((factor.score / meta.max) * 100))
                          return (
                            <div key={key}>
                              <div className="flex justify-between text-xs text-gray-400 mb-1">
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
                            </div>
                          )
                        })}
                      </div>

                      {breakdown.summary && (
                        <p className="mt-4 text-sm text-gray-400 italic border-t border-gray-700 pt-4">
                          {breakdown.summary}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-gray-500">No urgency breakdown available</p>
                  )}
                </div>
              </Section>

              {/* Duplicate Merge Info */}
              {report.corroboration_count > 0 && (
                <Section title="Duplicate Report Merge">
                  <div className="bg-indigo-900/20 border border-indigo-700/50 rounded-xl p-6">
                    <div className="flex items-start gap-3">
                      <span className="text-3xl">🔄</span>
                      <div>
                        <h4 className="text-lg font-semibold text-white mb-2">
                          AI merged {report.corroboration_count} duplicate report{report.corroboration_count !== 1 ? 's' : ''} into this incident
                        </h4>
                        <p className="text-sm text-gray-300 mb-3">
                          Multiple people reported the same incident from nearby locations. 
                          The AI used geo-proximity analysis and text similarity (TF-IDF) to 
                          identify these as duplicates and merged them to increase confidence.
                        </p>
                        <p className="text-xs text-indigo-400">
                          This corroboration added +{Math.min(report.corroboration_count * 5, 20)} points to the urgency score.
                        </p>
                      </div>
                    </div>
                  </div>
                </Section>
              )}

              {/* Incident Timeline */}
              <Section title="Incident Timeline">
                <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-6">
                  <div className="space-y-4">
                    <TimelineEvent
                      time={report.created_at}
                      label="Report Received"
                      detail={`Via ${report.source?.toUpperCase()}`}
                      icon="📥"
                    />
                    {report.updated_at && report.updated_at !== report.created_at && (
                      <TimelineEvent
                        time={report.updated_at}
                        label="Status Updated"
                        detail={report.status?.replace('_', ' ')}
                        icon="🔄"
                      />
                    )}
                    {report.verification_status !== 'unverified' && (
                      <TimelineEvent
                        time={report.updated_at || report.created_at}
                        label="Verification Complete"
                        detail={vInfo.label}
                        icon={vInfo.icon}
                      />
                    )}
                    {report.assigned_team && (
                      <TimelineEvent
                        time={report.updated_at || report.created_at}
                        label="Team Assigned"
                        detail={report.assigned_team}
                        icon="🚁"
                      />
                    )}
                  </div>
                </div>
              </Section>

            </div>

            {/* Sidebar - 1 column */}
            <div className="space-y-6">
              
              {/* Status Actions */}
              <Section title="Update Status">
                <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4">
                  <div className="space-y-2">
                    <ActionButton
                      label="▶ In Progress"
                      value="in_progress"
                      state={actionState}
                      current={report.status}
                      onClick={() => handleStatusChange('in_progress')}
                      className="bg-amber-700 hover:bg-amber-600 text-white"
                    />
                    <ActionButton
                      label="✔ Resolved"
                      value="resolved"
                      state={actionState}
                      current={report.status}
                      onClick={() => handleStatusChange('resolved')}
                      className="bg-green-700 hover:bg-green-600 text-white"
                    />
                    <ActionButton
                      label="✕ False Report"
                      value="false_report"
                      state={actionState}
                      current={report.status}
                      onClick={() => handleStatusChange('false_report')}
                      className="bg-gray-700 hover:bg-gray-600 text-gray-300"
                    />
                  </div>
                </div>
              </Section>

              {/* Recommended Teams */}
              <Section title="Recommended Teams">
                <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4">
                  {recommendations.length > 0 ? (
                    <div className="space-y-2">
                      {recommendations.map(team => (
                        <div
                          key={team.team_id}
                          className="bg-gray-800/60 rounded-lg px-3 py-3 border border-gray-700/50"
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="min-w-0">
                              <p className="text-sm font-semibold text-gray-200">{team.team_name}</p>
                              <p className="text-xs text-gray-500">
                                <span className={`font-semibold ${TEAM_TYPE_COLORS[team.team_type] ?? 'text-gray-400'}`}>
                                  {team.team_type}
                                </span>
                                {' · '}Cap {team.capacity}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-400">
                              {team.distance_km} km · {team.eta_estimate}
                            </span>
                            <button
                              onClick={() => handleAssign(team.team_id, team.team_name)}
                              disabled={assignState === 'loading'}
                              className="text-xs bg-indigo-700 hover:bg-indigo-600 text-white 
                                       font-semibold px-3 py-1 rounded transition-colors
                                       disabled:opacity-50"
                            >
                              Assign
                            </button>
                          </div>
                        </div>
                      ))}
                      {assignState?.teamName && (
                        <p className="text-xs text-green-400 mt-2">
                          ✓ Assigned to {assignState.teamName}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500">
                      {report.location?.latitude 
                        ? 'No available teams nearby'
                        : 'No GPS coordinates available'
                      }
                    </p>
                  )}
                </div>
              </Section>

              {/* Report Meta */}
              <Section title="Technical Details">
                <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4">
                  <dl className="space-y-2 text-xs">
                    <MetaRow label="Report ID" value={report.id} />
                    <MetaRow label="Created" value={new Date(report.created_at).toLocaleString()} />
                    <MetaRow label="Last Updated" value={new Date(report.updated_at).toLocaleString()} />
                    {report.location?.latitude && (
                      <MetaRow
                        label="GPS Coordinates"
                        value={`${report.location.latitude.toFixed(4)}, ${report.location.longitude.toFixed(4)}`}
                      />
                    )}
                  </dl>
                </div>
              </Section>

            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      {title && (
        <h2 className="text-lg font-bold text-white mb-3">{title}</h2>
      )}
      {children}
    </div>
  )
}

function TimelineEvent({ time, label, detail, icon }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-indigo-900/50 border-2 border-indigo-600/50 
                        flex items-center justify-center text-sm">
          {icon}
        </div>
        <div className="w-0.5 h-full bg-gray-700 mt-1" />
      </div>
      <div className="pb-4">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="text-xs text-gray-400">{detail}</p>
        <p className="text-[10px] text-gray-600 mt-1">
          {new Date(time).toLocaleString()}
        </p>
      </div>
    </div>
  )
}

function ActionButton({ label, value, state, current, onClick, className }) {
  const btnState = state[value]
  const isDisabled = btnState === 'loading' || btnState === 'done' || current === value
  
  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className={`w-full text-sm font-semibold px-4 py-2 rounded-lg transition-colors
                  disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
    >
      {btnState === 'loading' ? 'Processing…' : btnState === 'done' ? '✓ Done' : label}
    </button>
  )
}

function MetaRow({ label, value }) {
  return (
    <div>
      <dt className="text-gray-600 mb-0.5">{label}</dt>
      <dd className="text-gray-300 font-mono text-[11px] break-all">{value ?? '—'}</dd>
    </div>
  )
}
