/**
 * AIInsights — Screen 4
 *
 * Shows computed insights from real backend data.
 * ALL numbers must come from actual API data or aggregations.
 * NO hardcoded or fabricated statistics allowed.
 */

import { useState, useEffect } from 'react'
import { USE_MOCK, MOCK_SUMMARY, MOCK_REPORTS } from '../data/mockData'
import Navigation from './Navigation'

export default function AIInsights() {
  const [summary, setSummary] = useState(null)
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadData() {
      if (USE_MOCK) {
        setSummary(MOCK_SUMMARY)
        setReports(MOCK_REPORTS)
        setLoading(false)
        return
      }

      try {
        const [summaryRes, reportsRes] = await Promise.all([
          fetch('/api/stats/summary'),
          fetch('/api/reports?limit=1000'),
        ])

        if (!summaryRes.ok || !reportsRes.ok) {
          throw new Error('Failed to load data')
        }

        const summaryData = await summaryRes.json()
        const reportsData = await reportsRes.json()
        const reportsArray = Array.isArray(reportsData) ? reportsData : (reportsData.reports ?? [])

        setSummary(summaryData)
        setReports(reportsArray)
        setLoading(false)
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }

    loadData()
  }, [])

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

  if (error) {
    return (
      <div className="flex flex-col h-screen bg-gray-950 text-gray-200">
        <Navigation />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-400 text-lg mb-2">⚠️ Failed to load insights</p>
            <p className="text-gray-500 text-sm">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  // Compute real insights from actual data
  const insights = computeInsights(summary, reports)

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-200">
      <Navigation />
      
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">AI Insights</h1>
            <p className="text-gray-400">
              Real-time analytics from the AI disaster response pipeline
            </p>
          </div>

          {/* Insight Cards Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <InsightCard
              icon="🔄"
              title="Duplicate Reports Merged"
              value={insights.duplicatesMerged}
              subtitle={`${insights.duplicatesMerged} reports identified as duplicates`}
              color="purple"
            />
            
            <InsightCard
              icon="👥"
              title="Vulnerable Cases Flagged"
              value={insights.vulnerableCases}
              subtitle={`${insights.totalVulnerableFlags} vulnerable individuals identified`}
              color="pink"
            />

            <InsightCard
              icon="✅"
              title="Verified Reports"
              value={insights.verifiedReports}
              subtitle={`${insights.verificationRate}% of reports verified by external data`}
              color="green"
            />

            <InsightCard
              icon="🎯"
              title="Average Urgency Score"
              value={insights.avgUrgency}
              subtitle="Across all active reports"
              color="orange"
            />

            <InsightCard
              icon="👤"
              title="Total People Affected"
              value={insights.totalPeople}
              subtitle="Sum of all reported incidents"
              color="blue"
            />

            <InsightCard
              icon="⏱️"
              title="Critical Alerts"
              value={insights.criticalCount}
              subtitle={`Urgency score ≥ 80`}
              color="red"
            />
          </div>

          {/* Breakdown Sections */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* By Disaster Type */}
            <BreakdownCard
              title="Reports by Disaster Type"
              data={insights.byType}
              total={summary?.reports?.active ?? reports.filter(r => r.status !== 'resolved' && r.status !== 'false_report').length}
            />

            {/* By Verification Status */}
            <BreakdownCard
              title="Reports by Verification"
              data={insights.byVerification}
              total={summary?.reports?.active ?? reports.filter(r => r.status !== 'resolved' && r.status !== 'false_report').length}
            />
          </div>

          {/* AI Performance Metrics */}
          <div className="mt-6 bg-gray-900/60 border border-gray-700/60 rounded-xl p-6">
            <h3 className="text-lg font-bold text-white mb-4">AI Pipeline Performance</h3>
            <div className="grid md:grid-cols-4 gap-4">
              <MetricItem
                label="Corroboration Rate"
                value={insights.corroborationRate}
                unit="%"
                desc="Reports with multiple sources"
              />
              <MetricItem
                label="Avg Response Time"
                value={insights.avgResponseTime}
                unit="min"
                desc="Time to first action"
              />
              <MetricItem
                label="Team Utilization"
                value={insights.teamUtilization}
                unit="%"
                desc="Teams currently deployed"
              />
              <MetricItem
                label="Resolution Rate"
                value={insights.resolutionRate}
                unit="%"
                desc="Reports marked resolved"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Compute all insights from real data - NO FABRICATION ALLOWED
function computeInsights(summary, reports) {
  const activeReports = reports.filter(r => 
    r.status !== 'resolved' && r.status !== 'false_report'
  )

  // Duplicate reports merged
  const duplicatesMerged = reports.filter(r => r.is_duplicate_of !== null).length

  // Vulnerable cases
  const vulnerableCases = reports.filter(r => 
    r.vulnerable_flags && r.vulnerable_flags.length > 0
  ).length
  const totalVulnerableFlags = reports.reduce((sum, r) => 
    sum + (r.vulnerable_flags?.length ?? 0), 0
  )

  // Verified reports
  const verifiedReports = reports.filter(r => 
    r.verification_status && r.verification_status !== 'unverified'
  ).length
  const verificationRate = reports.length > 0 
    ? Math.round((verifiedReports / reports.length) * 100) 
    : 0

  // Average urgency
  const scores = reports.map(r => r.urgency?.score ?? r.urgency_score ?? 0)
  const avgUrgency = scores.length > 0
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : 0

  // Total people affected
  const totalPeople = reports.reduce((sum, r) => 
    sum + (r.num_people ?? 0), 0
  )

  // Critical count
  const criticalCount = reports.filter(r => 
    (r.urgency?.score ?? r.urgency_score ?? 0) >= 80
  ).length

  // By type
  const byType = summary?.reports?.by_type ?? {}

  // By verification
  const byVerification = summary?.reports?.by_verification ?? {}

  // Corroboration rate
  const reportsWithCorroboration = reports.filter(r => 
    r.corroboration_count && r.corroboration_count > 0
  ).length
  const corroborationRate = reports.length > 0
    ? Math.round((reportsWithCorroboration / reports.length) * 100)
    : 0

  // Response time (time from created to first status change)
  const responseTimes = reports
    .filter(r => r.updated_at && r.created_at && r.updated_at !== r.created_at)
    .map(r => {
      const created = new Date(r.created_at).getTime()
      const updated = new Date(r.updated_at).getTime()
      return (updated - created) / 60000 // minutes
    })
  const avgResponseTime = responseTimes.length > 0
    ? Math.round(responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length)
    : 0

  // Team utilization
  const teamsTotal = summary?.teams?.total ?? 0
  const teamsDeployed = summary?.teams?.deployed ?? 0
  const teamUtilization = teamsTotal > 0
    ? Math.round((teamsDeployed / teamsTotal) * 100)
    : 0

  // Resolution rate
  const resolvedCount = reports.filter(r => r.status === 'resolved').length
  const resolutionRate = reports.length > 0
    ? Math.round((resolvedCount / reports.length) * 100)
    : 0

  return {
    duplicatesMerged,
    vulnerableCases,
    totalVulnerableFlags,
    verifiedReports,
    verificationRate,
    avgUrgency,
    totalPeople,
    criticalCount,
    byType,
    byVerification,
    corroborationRate,
    avgResponseTime,
    teamUtilization,
    resolutionRate,
  }
}

function InsightCard({ icon, title, value, subtitle, color }) {
  const colorClasses = {
    purple: 'from-purple-900/40 to-purple-800/20 border-purple-700/50',
    pink: 'from-pink-900/40 to-pink-800/20 border-pink-700/50',
    green: 'from-green-900/40 to-green-800/20 border-green-700/50',
    orange: 'from-orange-900/40 to-orange-800/20 border-orange-700/50',
    blue: 'from-blue-900/40 to-blue-800/20 border-blue-700/50',
    red: 'from-red-900/40 to-red-800/20 border-red-700/50',
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} border rounded-xl p-6`}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-4xl">{icon}</span>
      </div>
      <h3 className="text-sm font-medium text-gray-400 mb-2">{title}</h3>
      <p className="text-4xl font-bold text-white mb-1 tabular-nums">{value}</p>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
  )
}

function BreakdownCard({ title, data, total }) {
  const items = Object.entries(data).map(([key, value]) => ({
    label: key.replace('_', ' '),
    value,
    percent: total > 0 ? Math.round((value / total) * 100) : 0,
  })).sort((a, b) => b.value - a.value)

  return (
    <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-6">
      <h3 className="text-lg font-bold text-white mb-4">{title}</h3>
      <div className="space-y-3">
        {items.map(item => (
          <div key={item.label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-300 capitalize">{item.label}</span>
              <span className="text-white font-semibold tabular-nums">{item.value}</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${item.percent}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MetricItem({ label, value, unit, desc }) {
  return (
    <div>
      <p className="text-2xl font-bold text-white tabular-nums">
        {value}<span className="text-sm text-gray-400 ml-1">{unit}</span>
      </p>
      <p className="text-xs font-medium text-gray-400 mt-1">{label}</p>
      <p className="text-[10px] text-gray-600 mt-0.5">{desc}</p>
    </div>
  )
}
