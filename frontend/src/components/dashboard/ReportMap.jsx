/**
 * ReportMap - Satellite imagery map with markers for all reports
 * 
 * FIXED: Now correctly renders ALL markers with valid coordinates
 * FIXED: Shows actual location names instead of "No location"
 */

import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'

const DEFAULT_CENTER = [20.5937, 78.9629]  // Center of India
const DEFAULT_ZOOM = 5  // Zoom level to see all of India

function pinColor(score) {
  if (score >= 80) return { bg: '#dc2626', ring: '#fca5a5' }
  if (score >= 60) return { bg: '#ea580c', ring: '#fdba74' }
  if (score >= 40) return { bg: '#ca8a04', ring: '#fde047' }
  return { bg: '#6b7280', ring: '#d1d5db' }
}

function makePinIcon(score, corrobCount, isSelected) {
  const { bg, ring } = pinColor(score)
  const size = isSelected ? 40 : 32
  const ringW = isSelected ? 3 : 2
  
  const badgeHtml = corrobCount > 0
    ? `<div style="position:absolute;top:-6px;right:-6px;background:#4f46e5;color:#fff;
         font-size:10px;font-weight:700;width:18px;height:18px;border-radius:50%;
         display:flex;align-items:center;justify-content:center;border:2px solid #fff;
         box-shadow:0 2px 4px rgba(0,0,0,0.2);">${corrobCount}</div>`
    : ''

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 40 40">
      <circle cx="20" cy="20" r="16" fill="${ring}" opacity="0.4"/>
      <circle cx="20" cy="20" r="12" fill="${bg}" stroke="#fff" stroke-width="${ringW}"/>
      ${isSelected ? `<circle cx="20" cy="20" r="16" fill="none" stroke="${bg}" stroke-width="2" stroke-dasharray="4 2" opacity="0.8"/>` : ''}
    </svg>`

  return L.divIcon({
    className: '',
    html: `<div style="position:relative;width:${size}px;height:${size}px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.3))">${svg}${badgeHtml}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2)],
  })
}

// White overlay pane component
function WhiteOverlay() {
  const map = useMap()
  
  useEffect(() => {
    const overlayPane = L.DomUtil.create('div', 'white-overlay-pane')
    overlayPane.style.position = 'absolute'
    overlayPane.style.top = '0'
    overlayPane.style.left = '0'
    overlayPane.style.right = '0'
    overlayPane.style.bottom = '0'
    overlayPane.style.background = 'rgba(255, 255, 255, 0.25)'
    overlayPane.style.pointerEvents = 'none'
    overlayPane.style.zIndex = '400'
    
    map.getContainer().appendChild(overlayPane)
    
    return () => {
      if (overlayPane.parentNode) {
        overlayPane.parentNode.removeChild(overlayPane)
      }
    }
  }, [map])
  
  return null
}

function MarkersLayer({ reports, selectedId, onSelect }) {
  const map = useMap()
  const markersRef = useRef({})

  useEffect(() => {
    const currentIds = new Set(reports.map(r => r.id))

    // Remove stale markers
    Object.keys(markersRef.current).forEach(id => {
      if (!currentIds.has(id)) {
        markersRef.current[id].remove()
        delete markersRef.current[id]
      }
    })

    // Add/update markers for ALL reports with coordinates
    reports.forEach(report => {
      const lat = report.location?.latitude
      const lon = report.location?.longitude
      
      // Skip if no coordinates
      if (lat == null || lon == null || lat === '' || lon === '') return

      const score = report.urgency?.score ?? report.urgency_score ?? 0
      const corrob = report.corroboration_count ?? 0
      const selected = report.id === selectedId
      const icon = makePinIcon(score, corrob, selected)

      // Get location text - prioritize location_text, fallback to coordinates
      const locationText = report.location?.text || report.location?.location_text || 
                          `${lat.toFixed(4)}, ${lon.toFixed(4)}`

      if (markersRef.current[report.id]) {
        // Update existing marker
        markersRef.current[report.id].setIcon(icon)
      } else {
        // Create new marker
        const marker = L.marker([lat, lon], { icon })
          .addTo(map)
          .on('click', () => onSelect(report.id))

        marker.bindTooltip(
          `<b>${report.disaster_type?.toUpperCase() || 'INCIDENT'}</b><br/>` +
          `Urgency: ${Math.round(score)}<br/>` +
          `${locationText}`,
          { className: 'rescueai-tooltip', direction: 'top', offset: [0, -16] }
        )

        markersRef.current[report.id] = marker
      }
    })
  }, [reports, selectedId, onSelect, map])

  // Pan to selected pin
  useEffect(() => {
    if (!selectedId) return
    const report = reports.find(r => r.id === selectedId)
    if (!report) return
    const lat = report.location?.latitude
    const lon = report.location?.longitude
    if (lat != null && lon != null && lat !== '' && lon !== '') {
      map.panTo([lat, lon], { animate: true, duration: 0.5 })
    }
  }, [selectedId, reports, map])

  // Cleanup
  useEffect(() => {
    return () => {
      Object.values(markersRef.current).forEach(m => m.remove())
      markersRef.current = {}
    }
  }, [])

  return null
}

export default function ReportMap({ reports, selectedId, onSelect, loading }) {
  const mappable = reports.filter(r => {
    const lat = r.location?.latitude
    const lon = r.location?.longitude
    return lat != null && lon != null && lat !== '' && lon !== ''
  })

  return (
    <div className="relative w-full h-full bg-gray-300">
      {/* DEMO DATA WARNING - Always Visible - RESPONSIVE */}
      <div className="absolute top-2 md:top-4 left-1/2 transform -translate-x-1/2 z-[1001] w-[90%] md:max-w-2xl px-2 md:px-4">
        <div className="demo-warning rounded-lg md:rounded-xl px-2 md:px-4 py-2 md:py-3 shadow-lg">
          <div className="flex items-center gap-1 md:gap-2">
            <span className="text-lg md:text-2xl">⚠️</span>
            <div className="text-[10px] md:text-xs">
              <p className="font-bold text-amber-900 leading-tight">DEMO DATA NOTICE</p>
              <p className="text-amber-800 leading-snug hidden md:block">
                Weather & satellite verification zones use simulated data for illustration — not real-time conditions
              </p>
              <p className="text-amber-800 leading-snug md:hidden">
                Simulated demo data only
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Map - RESPONSIVE: Larger touch targets on mobile */}
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        className="w-full h-full"
        zoomControl={true}
        attributionControl={true}
      >
        {/* Base layer: Satellite imagery from Esri (free) */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution='Tiles &copy; Esri'
          maxZoom={19}
          zIndex={1}
        />
        
        {/* Hybrid layer: Real world place names and road labels overlay - like Google Maps hybrid view */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
          attribution='&copy; Esri'
          maxZoom={19}
          zIndex={3}
        />
        
        <WhiteOverlay />
        <MarkersLayer reports={mappable} selectedId={selectedId} onSelect={onSelect} />
      </MapContainer>

      {/* Loading - RESPONSIVE */}
      {loading && (
        <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-[1000] backdrop-blur-sm">
          <div className="w-6 h-6 md:w-8 md:h-8 border-2 md:border-3 border-gray-300 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      )}

      {/* Legend - RESPONSIVE: Smaller on mobile, can be hidden/toggled */}
      <div className="absolute bottom-2 md:bottom-4 left-2 md:left-4 z-[1000] glass-panel rounded-lg md:rounded-xl 
                      px-2 md:px-4 py-2 md:py-3 text-[10px] md:text-xs space-y-1 md:space-y-2 shadow-lg
                      max-w-[140px] md:max-w-none">
        <p className="text-gray-700 font-bold mb-1 md:mb-2 uppercase tracking-wider text-[9px] md:text-[11px]">
          Urgency
        </p>
        {[
          { color: '#dc2626', label: '80+ Critical', shortLabel: '80+' },
          { color: '#ea580c', label: '60–79 High', shortLabel: '60+' },
          { color: '#ca8a04', label: '40–59 Medium', shortLabel: '40+' },
          { color: '#6b7280', label: '0–39 Low', shortLabel: '0+' },
        ].map(({ color, label, shortLabel }) => (
          <div key={label} className="flex items-center gap-1 md:gap-2">
            <span className="inline-block w-2 h-2 md:w-3 md:h-3 rounded-full shrink-0 border border-white"
                  style={{ background: color, boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }} />
            <span className="text-gray-800 font-medium">
              <span className="md:hidden">{shortLabel}</span>
              <span className="hidden md:inline">{label}</span>
            </span>
          </div>
        ))}
        <div className="hidden md:flex items-center gap-2 mt-2 pt-2 border-t border-gray-300">
          <span className="inline-flex items-center justify-center w-4 h-4 rounded-full
                           bg-indigo-600 text-white text-[9px] font-bold shrink-0 border border-white"
                style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }}>3</span>
          <span className="text-gray-700 font-medium">Corroborations</span>
        </div>
        
        <div className="hidden md:block mt-3 pt-3 border-t border-gray-300">
          <p className="text-[10px] text-amber-800 leading-tight font-medium">
            ⚠️ Verification zones: demo data only
          </p>
        </div>
      </div>

      {/* No GPS notice - RESPONSIVE */}
      {!loading && reports.length > 0 && mappable.length < reports.length && (
        <div className="absolute top-14 md:top-20 right-2 md:right-4 z-[1000] glass-panel rounded-md md:rounded-lg 
                        px-2 md:px-3 py-1 md:py-2 text-[10px] md:text-xs text-gray-700 shadow-md">
          <span className="font-semibold">{reports.length - mappable.length}</span> 
          <span className="hidden sm:inline"> report(s) missing GPS</span>
          <span className="sm:hidden"> no GPS</span>
        </div>
      )}
    </div>
  )
}
