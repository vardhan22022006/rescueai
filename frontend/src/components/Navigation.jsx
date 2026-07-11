/**
 * Navigation
 *
 * Top navigation bar shared across all main screens
 * Light grey/glossy aesthetic
 * Responsive: hamburger menu on mobile, top bar on desktop
 */

import { NavLink } from 'react-router-dom'
import { useState } from 'react'

const NAV_LINKS = [
  { to: '/', label: 'How It Works', icon: '💡' },
  { to: '/command-center', label: 'Command Center', icon: '🎯' },
  { to: '/insights', label: 'AI Insights', icon: '📊' },
]

export default function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <nav className="glass-panel-dark border-b border-gray-300 px-4 py-3 shrink-0 shadow-sm">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span className="text-2xl">🚨</span>
          <span className="font-bold text-gray-900 hidden sm:inline">RescueAI</span>
        </div>

        {/* Desktop Navigation - hidden on mobile */}
        <div className="desktop-nav flex items-center gap-1">
          {NAV_LINKS.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all
                 ${isActive
                   ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md'
                   : 'text-gray-700 hover:text-gray-900 hover:bg-white/50'
                 }`
              }
            >
              <span className="text-base">{link.icon}</span>
              <span className="hidden lg:inline">{link.label}</span>
            </NavLink>
          ))}
        </div>

        {/* Desktop Citizen Report Button */}
        <NavLink
          to="/report"
          className="hidden md:flex items-center gap-1 text-xs font-semibold bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800
                     text-white px-4 py-2 rounded-xl transition-all shadow-md hover:shadow-lg"
        >
          <span>📱</span>
          <span className="hidden lg:inline">Citizen Report</span>
        </NavLink>

        {/* Mobile Hamburger Button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="mobile-menu-button text-gray-700 hover:text-gray-900 p-2"
          aria-label="Toggle menu"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {mobileMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Menu - slides down on mobile only */}
      {mobileMenuOpen && (
        <div className="mobile-menu md:hidden mt-3 pb-3 space-y-2">
          {NAV_LINKS.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-base font-semibold transition-all
                 ${isActive
                   ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md'
                   : 'text-gray-700 hover:text-gray-900 hover:bg-white/50'
                 }`
              }
            >
              <span className="text-xl">{link.icon}</span>
              <span>{link.label}</span>
            </NavLink>
          ))}
          <NavLink
            to="/report"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center gap-3 text-base font-semibold bg-gradient-to-r from-emerald-600 to-emerald-700
                       text-white px-4 py-3 rounded-xl shadow-md"
          >
            <span className="text-xl">📱</span>
            <span>Citizen Report</span>
          </NavLink>
        </div>
      )}
    </nav>
  )
}
