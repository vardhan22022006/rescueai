/**
 * HowItWorks — Screen 1
 *
 * Landing page with:
 * - Full-width hero section with satellite imagery background
 * - Single unified AI pipeline with example data integrated into each stage
 * - Clean, minimal, presentation-ready design
 * 
 * FIXED: Merged two repetitive pipeline sections into ONE flow
 * FIXED: Added hero section with background image and gradient overlay
 */

import { useNavigate } from 'react-router-dom'

const PIPELINE_STAGES = [
  {
    icon: '📱',
    title: 'Reports In',
    desc: 'SMS/App/Voice',
    example: 'SMS received:\n"Water entered my house, grandmother trapped"',
  },
  {
    icon: '✓',
    title: 'AI Verifies',
    desc: 'Weather + Satellite',
    example: 'Weather API confirms heavy rainfall in area',
  },
  {
    icon: '🔍',
    title: 'Deduplicates',
    desc: 'Merges Similar',
    example: '3 similar reports merged into one incident',
  },
  {
    icon: '🎯',
    title: 'Scores Urgency',
    desc: 'People + Risk',
    example: 'Urgency: 87/100\n(Vulnerable: elderly, flood risk)',
  },
  {
    icon: '🚁',
    title: 'Finds Team',
    desc: 'Nearest Available',
    example: 'NDRF Alpha Team\n4.2 km away',
  },
  {
    icon: '👥',
    title: 'Dispatches',
    desc: 'Human Decision',
    example: 'Team assigned by dispatcher',
  },
  {
    icon: '✅',
    title: 'Resolves',
    desc: 'Mission Complete',
    example: 'Rescue completed, 2 people evacuated',
  },
]

export default function HowItWorks() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* HERO SECTION - Full-width with background image - RESPONSIVE */}
      <div 
        className="relative bg-cover bg-center min-h-[400px] md:min-h-[500px] flex items-center justify-center"
        style={{
          backgroundImage: `url(/images/hero-aerial.jpg), url(https://images.unsplash.com/photo-1547683905-f686c993aae5?w=1920&q=80)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
      >
        {/* Dark gradient overlay for text readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-gray-900/80 via-gray-900/70 to-gray-900/80" />
        
        {/* Hero content - RESPONSIVE */}
        <div className="relative z-10 text-center px-4 sm:px-6 py-12 md:py-20">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black text-white mb-4 md:mb-6 tracking-tight drop-shadow-2xl">
            🚨 RescueAI
          </h1>
          <p className="text-xl sm:text-2xl md:text-3xl text-white mb-3 md:mb-4 font-bold drop-shadow-lg">
            AI-Powered Disaster Response
          </p>
          <p className="text-sm sm:text-base text-gray-200 max-w-3xl mx-auto leading-relaxed mb-8 md:mb-10 drop-shadow-md px-4">
            During disasters, emergency rooms receive thousands of reports.
            RescueAI uses AI to verify, deduplicate, score, and route them
            so the right team reaches the right people first.
          </p>
          
          {/* CTA Buttons - RESPONSIVE */}
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center px-4">
            <button
              onClick={() => navigate('/command-center')}
              className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-6 sm:px-8 py-3 sm:py-4 
                         rounded-full text-base sm:text-lg transition-all duration-300 shadow-2xl 
                         hover:shadow-indigo-500/50 transform hover:scale-105"
            >
              Enter Command Center →
            </button>
            <button
              onClick={() => document.getElementById('pipeline')?.scrollIntoView({ behavior: 'smooth' })}
              className="w-full sm:w-auto bg-transparent hover:bg-white/10 text-white font-bold px-6 sm:px-8 py-3 sm:py-4 
                         rounded-full text-base sm:text-lg border-2 border-white/80 transition-all duration-300
                         shadow-lg hover:shadow-white/30"
            >
              Learn How It Works
            </button>
          </div>
        </div>
      </div>

      {/* PIPELINE SECTION - Unified flow with example data - RESPONSIVE */}
      <div id="pipeline" className="max-w-6xl mx-auto px-4 sm:px-6 py-12 md:py-20">
        <div className="text-center mb-8 md:mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2 md:mb-3">
            The AI Pipeline
          </h2>
          <p className="text-sm text-gray-600 max-w-2xl mx-auto px-4">
            Seven stages from incoming report to rescue completion
          </p>
        </div>

        {/* ILLUSTRATIVE SCENARIO BADGE - Always visible - RESPONSIVE */}
        <div className="demo-warning rounded-xl p-3 sm:p-4 mb-8 md:mb-10 max-w-4xl mx-auto">
          <div className="flex items-center justify-center gap-2 sm:gap-3">
            <span className="text-xl sm:text-2xl">💡</span>
            <div className="text-center">
              <p className="text-xs sm:text-sm font-bold text-amber-900 leading-tight">
                ILLUSTRATIVE SCENARIO — NOT LIVE DATA
              </p>
              <p className="text-[10px] sm:text-xs text-amber-800 leading-snug">
                The example values below demonstrate how the pipeline processes a report
              </p>
            </div>
          </div>
        </div>

        {/* Unified Pipeline Cards - RESPONSIVE: vertical on mobile, horizontal on desktop */}
        <div className="relative mb-12 md:mb-16">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-7 gap-4 md:gap-6">
            {PIPELINE_STAGES.map((stage, idx) => (
              <div key={idx} className="relative">
                {/* Stage Card */}
                <div className="glass-panel rounded-2xl p-4 sm:p-6 shadow-lg hover:shadow-xl 
                                transition-all duration-300 h-full flex flex-col">
                  {/* Icon */}
                  <div className="text-center mb-3 sm:mb-4">
                    <div className="text-4xl sm:text-5xl mb-2 sm:mb-3">{stage.icon}</div>
                    <h3 className="text-sm font-bold text-gray-900 mb-1 leading-tight">
                      {stage.title}
                    </h3>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      {stage.desc}
                    </p>
                  </div>
                  
                  {/* Example Data - integrated directly */}
                  <div className="mt-auto pt-3 sm:pt-4 border-t border-gray-200">
                    <p className="text-[10px] text-gray-700 font-medium leading-tight whitespace-pre-line text-center">
                      {stage.example}
                    </p>
                  </div>
                </div>
                
                {/* Arrow between stages (desktop only) */}
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 transform -translate-y-1/2 z-10">
                    <div className="text-2xl lg:text-3xl text-gray-400">→</div>
                  </div>
                )}
                
                {/* Down arrow on mobile between stages */}
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div className="md:hidden flex justify-center my-2">
                    <div className="text-2xl text-gray-400">↓</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Key Features - Simplified - RESPONSIVE */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 md:gap-8 max-w-4xl mx-auto">
          <FeatureCard
            icon="🌐"
            title="Multi-Channel Intake"
            desc="SMS, WhatsApp, voice, web"
          />
          <FeatureCard
            icon="🔒"
            title="Explainable AI"
            desc="Every score shows reasoning"
          />
          <FeatureCard
            icon="⚡"
            title="Real-Time Processing"
            desc="Pipeline runs in seconds"
          />
        </div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, desc }) {
  return (
    <div className="glass-panel rounded-2xl p-6 sm:p-8 text-center shadow-lg hover:shadow-xl 
                    transition-shadow duration-300 border border-gray-200">
      <div className="text-3xl sm:text-4xl mb-3 sm:mb-4">{icon}</div>
      <h3 className="text-sm font-bold text-gray-900 mb-2">{title}</h3>
      <p className="text-xs text-gray-600">{desc}</p>
    </div>
  )
}
