/**
 * PriorityQueue
 *
 * Right panel — scrollable list of reports sorted by urgency_score desc.
 * Each row shows:
 *   - Disaster type icon + urgency score badge
 *   - Vulnerable flags as small tags
 *   - Verification status icon
 *   - Time since reported
 *   - Num people
 *   - Status pill
 *
 * Clicking a row calls onSelect(report.id), which highlights the pin
 * on the map and opens the CaseDetail panel.
 * 
 * RESPONSIVE: On mobile, takes full screen when in Queue tab. Touch-friendly rows with 44px minimum height.
 */

// ---------------------------------------------------------------------------
// Shared helpers (also used by other components — keep in sync)
// ---------------------------------------------------------------------------
export const DISASTER_ICONS = {
  flood:      '🌊',
  earthquake: '🌍',
  cyclone:    '🌀',
  other:      '⚠️',
}

export const VERIFICATION_ICONS = {
  unverified:          { icon: '❓', label: 'Unverified',          color: 'text-gray-400' },
  corroborated:        { icon: '👥', label: 'Corroborated',        color: 'text-blue-400' },
  weather_confirmed:   { icon: '🌦️', label: 'Weather Confirmed',   color: 'text-cyan-400' },
  satellite_confirmed: { icon: '🛰️', label: 'Satellite Confirmed', color: 'text-green-400' },
}

export const VULNERABLE_COLORS = {
  elderly:  'bg-orange-100 text-orange-700 border-orange-300',
  child:    'bg-yellow-100 text-yellow-700 border-yellow-300',
  pregnant: 'bg-pink-100   text-pink-700   border-pink-300',
  disabled: 'bg-purple-100 text-purple-700 border-purple-300',
}

export function urgencyColor(score) {
  if (score >= 80) return 'bg-red-600     text-white'
  if (score >= 60) return 'bg-orange-500  text-white'
  if (score >= 40) return 'bg-yellow-500  text-gray-900'
  return                   'bg-gray-600   text-gray-300'
}

export function urgencyBorder(score) {
  if (score >= 80) return 'border-red-700/70'
  if (score >= 60) return 'border-orange-700/70'
  if (score >= 40) return 'border-yellow-700/70'
  return                   'border-gray-700/60'
}

export function timeAgo(isoString) {
  const diffMs  = Date.now() - new Date(isoString).getTime()
  const mins    = Math.floor(diffMs / 60000)
  if (mins < 1)   return 'just now'
  if (mins < 60)  return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs  < 24)  return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const STATUS_PILL = {
  new:          'bg-blue-100  text-blue-700  border-blue-300',
  in_progress:  'bg-amber-100 text-amber-700 border-amber-300',
  resolved:     'bg-green-100 text-green-700 border-green-300',
  false_report: 'bg-gray-200  text-gray-600  border-gray-300',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function PriorityQueue({ reports, selectedId, onSelect, loading }) {
  if (loading) {
    return (
      <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200">
        <QueueHeader count={0} />
        <div className="flex-1 flex items-center justify-center">
          <Spinner />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 md:border-l border-gray-200">
      <QueueHeader count={reports.length} />

      {reports.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-600 gap-2 px-6">
          <span className="text-3xl md:text-4xl">✅</span>
          <p className="text-sm md:text-base text-center">No active reports match the current filters.</p>
        </div>
      ) : (
        <ul className="flex-1 overflow-y-auto divide-y divide-gray-200">
          {reports.map(report => (
            <ReportRow
              key={report.id}
              report={report}
              selected={report.id === selectedId}
              onClick={() => onSelect(report.id)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function QueueHeader({ count }) {
  return (
    <div className="px-3 md:px-4 py-2 md:py-3 border-b border-gray-200 shrink-0 bg-white">
      <h2 className="text-xs md:text-sm font-semibold text-gray-700 uppercase tracking-widest">
        Priority Queue
        <span className="ml-2 text-gray-900 font-bold tabular-nums">{count}</span>
      </h2>
    </div>
  )
}

function ReportRow({ report, selected, onClick }) {
  const score  = report.urgency?.score ?? report.urgency_score ?? 0
  const vInfo  = VERIFICATION_ICONS[report.verification_status] ?? VERIFICATION_ICONS.unverified
  const flags  = report.vulnerable_flags ?? []
  const loc    = report.location?.text ?? report.location?.location_text ?? null

  return (
    <li>
      <button
        onClick={onClick}
        className={`w-full text-left px-3 md:px-4 py-3 md:py-3 transition-colors
          ${selected
            ? 'bg-indigo-50 border-l-4 md:border-l-2 border-l-indigo-500'
            : 'hover:bg-gray-100 border-l-4 md:border-l-2 border-l-transparent active:bg-indigo-100'
          }`}
        style={{ minHeight: '44px' }}
      >
        {/* Top row: icon + type, score badge, verification, time - RESPONSIVE */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-lg md:text-base leading-none shrink-0">
              {DISASTER_ICONS[report.disaster_type] ?? '⚠️'}
            </span>
            <span className="text-sm md:text-sm font-semibold text-gray-900 capitalize truncate">
              {report.disaster_type}
            </span>
          </div>
          <div className="flex items-center gap-1.5 md:gap-2 shrink-0">
            <span className={`text-xs md:text-xs font-bold px-2 py-1 rounded-full tabular-nums ${urgencyColor(score)}`}>
              {Math.round(score)}
            </span>
            <span
              className={`text-base md:text-sm ${vInfo.color}`}
              title={vInfo.label}
            >
              {vInfo.icon}
            </span>
          </div>
        </div>

        {/* Middle row: location text, num_people - RESPONSIVE */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <p className="text-xs md:text-xs text-gray-600 truncate max-w-[160px] md:max-w-[140px]">
            {loc ?? 'No location'}
          </p>
          {report.num_people != null && (
            <span className="text-xs md:text-xs text-gray-600 shrink-0">
              👤 {report.num_people}
            </span>
          )}
        </div>

        {/* Bottom row: vulnerable flags, status pill, time - RESPONSIVE */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1">
            {flags.map(f => (
              <span
                key={f}
                className={`text-[10px] md:text-[10px] px-1.5 py-0.5 rounded border font-medium capitalize
                            ${VULNERABLE_COLORS[f] ?? 'bg-gray-200 text-gray-700 border-gray-300'}`}
              >
                {f}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`text-[10px] md:text-[10px] px-1.5 py-0.5 rounded border capitalize
                              ${STATUS_PILL[report.status] ?? STATUS_PILL.new}`}>
              {report.status?.replace('_', ' ')}
            </span>
            <span className="text-[10px] md:text-[10px] text-gray-500 tabular-nums">
              {timeAgo(report.created_at)}
            </span>
          </div>
        </div>

        {/* Corroboration badge - RESPONSIVE */}
        {report.corroboration_count > 0 && (
          <div className="mt-1.5 flex items-center gap-1">
            <span className="text-[10px] md:text-[10px] bg-indigo-100 text-indigo-700 border border-indigo-300
                             px-1.5 py-0.5 rounded-full font-medium">
              +{report.corroboration_count} corroborating
            </span>
          </div>
        )}
      </button>
    </li>
  )
}

function Spinner() {
  return (
    <div className="w-8 h-8 md:w-6 md:h-6 border-3 md:border-2 border-gray-300 border-t-indigo-600 rounded-full animate-spin" />
  )
}
