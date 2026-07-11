/**
 * CitizenReport  — /report
 *
 * Mobile-first, large-text disaster reporting form for citizens.
 * No login required. Works offline: the service worker queues the POST
 * to IndexedDB and retries when connectivity is restored.
 *
 * Sections (in order):
 *  1. Language selector
 *  2. Location  — "Use my location" GPS button + manual text fallback
 *  3. Disaster type — large tappable icon tiles
 *  4. Description — free-text area with inline voice recording (Web Speech API)
 *  5. Number of people affected
 *  6. Vulnerable people checkboxes
 *  7. Phone number (optional)
 *  8. Send for Help — big red submit button
 *  9. Confirmation screen after submit
 */

import { useState, useRef, useCallback, useEffect } from 'react'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const LANGUAGES = [
  { code: 'en-IN', label: 'English' },
  { code: 'hi-IN', label: 'हिन्दी' },
  { code: 'mr-IN', label: 'मराठी' },
  { code: 'bn-IN', label: 'বাংলা' },
  { code: 'ta-IN', label: 'தமிழ்' },
  { code: 'te-IN', label: 'తెలుగు' },
  { code: 'gu-IN', label: 'ગુજરાતી' },
  { code: 'pa-IN', label: 'ਪੰਜਾਬੀ' },
]

const DISASTER_TYPES = [
  { value: 'flood',      emoji: '🌊', label: 'Flood',      labelHi: 'बाढ़' },
  { value: 'earthquake', emoji: '🌍', label: 'Earthquake',  labelHi: 'भूकंप' },
  { value: 'cyclone',    emoji: '🌀', label: 'Cyclone',     labelHi: 'चक्रवात' },
  { value: 'other',      emoji: '⚠️', label: 'Other',       labelHi: 'अन्य' },
]

const VULNERABLE_OPTIONS = [
  { value: 'elderly',  emoji: '👴', label: 'Someone elderly' },
  { value: 'child',    emoji: '👶', label: 'Child / baby' },
  { value: 'pregnant', emoji: '🤰', label: 'Pregnant person' },
  { value: 'disabled', emoji: '♿', label: 'Person with disability' },
]

// Web Speech API detection
const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null
const SPEECH_SUPPORTED = Boolean(SpeechRecognition)

// Form steps
const STEP = { FORM: 'form', SUBMITTING: 'submitting', SUCCESS: 'success' }

// ---------------------------------------------------------------------------
// Small reusable UI pieces
// ---------------------------------------------------------------------------
function SectionTitle({ step, children }) {
  return (
    <div className="flex items-center gap-3 mb-3">
      <span className="flex items-center justify-center w-7 h-7 rounded-full
                       bg-red-600 text-white text-sm font-bold shrink-0">
        {step}
      </span>
      <h2 className="text-lg font-bold text-gray-900">{children}</h2>
    </div>
  )
}

function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-200 p-5 ${className}`}>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Voice inline widget (self-contained — no import from VoiceReportForm)
// ---------------------------------------------------------------------------
function VoiceWidget({ language, onTranscript, disabled }) {
  const [listening, setListening] = useState(false)
  const [interim,   setInterim]   = useState('')
  const [error,     setError]     = useState('')
  const recRef = useRef(null)

  useEffect(() => () => recRef.current?.abort(), [])

  const start = useCallback(() => {
    if (!SpeechRecognition) return
    setError('')
    setInterim('')
    const r = new SpeechRecognition()
    r.lang            = language
    r.interimResults  = true
    r.continuous      = true
    r.maxAlternatives = 1

    r.onresult = e => {
      let fin = '', int = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript
        if (e.results[i].isFinal) fin += t + ' '
        else                       int += t
      }
      if (fin) onTranscript(fin)
      setInterim(int)
    }
    r.onerror = e => {
      if (e.error === 'no-speech' || e.error === 'aborted') return
      setError('Mic error: ' + e.error)
      setListening(false)
    }
    r.onend = () => { setInterim(''); setListening(false) }
    recRef.current = r
    r.start()
    setListening(true)
  }, [language, onTranscript])

  const stop = useCallback(() => {
    recRef.current?.stop()
    setListening(false)
  }, [])

  if (!SPEECH_SUPPORTED) {
    return (
      <p className="text-sm text-amber-700 bg-amber-50 rounded-xl px-4 py-2 border border-amber-200">
        🎤 Voice input works best in Chrome. Please type your message below.
      </p>
    )
  }

  return (
    <div>
      {error && (
        <p className="text-sm text-red-600 mb-2">⚠ {error}</p>
      )}
      <button
        type="button"
        onClick={listening ? stop : start}
        disabled={disabled}
        className={`flex items-center justify-center gap-2 w-full py-4 rounded-2xl
                    text-base font-bold transition-all
                    disabled:opacity-40 disabled:cursor-not-allowed
                    ${listening
                      ? 'bg-gray-800 text-white animate-pulse'
                      : 'bg-orange-100 text-orange-800 border-2 border-orange-300 hover:bg-orange-200'
                    }`}
      >
        {listening ? (
          <><StopIcon className="w-5 h-5" /> Stop Recording</>
        ) : (
          <><MicIcon className="w-5 h-5" /> 🎙️ Record Voice Message Instead</>
        )}
      </button>
      {listening && (
        <div className="mt-2 flex items-center gap-2 text-sm text-red-600 font-medium">
          <span className="inline-block w-2.5 h-2.5 bg-red-500 rounded-full animate-ping" />
          Listening… speak now
          {interim && <span className="text-gray-400 italic ml-1">{interim}</span>}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function CitizenReport() {
  // ── form state ──────────────────────────────────────────────────────────
  const [step,          setStep]          = useState(STEP.FORM)
  const [language,      setLanguage]      = useState('en-IN')
  const [locState,      setLocState]      = useState('idle') // idle|loading|done|denied
  const [latitude,      setLatitude]      = useState(null)
  const [longitude,     setLongitude]     = useState(null)
  const [locationText,  setLocationText]  = useState('')
  const [disasterType,  setDisasterType]  = useState(null)
  const [description,   setDescription]  = useState('')
  const [numPeople,     setNumPeople]     = useState('')
  const [vulnerable,    setVulnerable]    = useState(new Set())
  const [phone,         setPhone]         = useState('')
  const [errorMsg,      setErrorMsg]      = useState('')
  const [reportId,      setReportId]      = useState(null)
  const [wasQueued,     setWasQueued]     = useState(false)

  const isSubmitting = step === STEP.SUBMITTING
  const isSuccess    = step === STEP.SUCCESS

  // ── GPS ─────────────────────────────────────────────────────────────────
  const requestGPS = () => {
    if (!navigator.geolocation) {
      setLocState('denied')
      return
    }
    setLocState('loading')
    navigator.geolocation.getCurrentPosition(
      pos => {
        setLatitude(pos.coords.latitude)
        setLongitude(pos.coords.longitude)
        setLocState('done')
      },
      () => setLocState('denied'),
      { timeout: 10_000, maximumAge: 60_000 }
    )
  }

  // ── vulnerable checkboxes ────────────────────────────────────────────────
  const toggleVulnerable = value => {
    setVulnerable(prev => {
      const next = new Set(prev)
      next.has(value) ? next.delete(value) : next.add(value)
      return next
    })
  }

  // ── voice transcript appender ────────────────────────────────────────────
  const appendTranscript = useCallback(text => {
    setDescription(prev => (prev ? prev + ' ' + text.trim() : text.trim()))
  }, [])

  // ── submit ───────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setErrorMsg('')

    if (!disasterType) {
      setErrorMsg('Please select a disaster type.')
      return
    }
    if (!description.trim()) {
      setErrorMsg('Please describe what is happening.')
      return
    }

    setStep(STEP.SUBMITTING)

    const payload = {
      source:         'app',
      raw_text:       description.trim(),
      reporter_phone: phone.trim() || null,
      latitude:       latitude  ?? null,
      longitude:      longitude ?? null,
      location_text:  locationText.trim() || null,
      // These are sent as extra context — the backend NLP will also extract them,
      // but sending explicit values lets the backend skip extraction if it wants.
      disaster_type:  disasterType,
      num_people:     numPeople ? parseInt(numPeople, 10) : null,
      vulnerable_flags: [...vulnerable],
    }

    try {
      const res = await fetch('/api/reports/intake', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      })

      // 202 = queued by service worker (offline)
      const data = await res.json().catch(() => ({}))

      if (res.ok || res.status === 202) {
        setReportId(data.report_id ?? null)
        setWasQueued(data.queued === true)
        setStep(STEP.SUCCESS)
      } else {
        throw new Error(data.detail || `Server error ${res.status}`)
      }
    } catch (err) {
      setErrorMsg(`Could not send report: ${err.message}. Check your connection and try again.`)
      setStep(STEP.FORM)
    }
  }

  // ── reset ────────────────────────────────────────────────────────────────
  const reset = () => {
    setStep(STEP.FORM)
    setLanguage('en-IN')
    setLocState('idle')
    setLatitude(null)
    setLongitude(null)
    setLocationText('')
    setDisasterType(null)
    setDescription('')
    setNumPeople('')
    setVulnerable(new Set())
    setPhone('')
    setErrorMsg('')
    setReportId(null)
    setWasQueued(false)
  }

  // ── success screen ────────────────────────────────────────────────────────
  if (isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-5 py-12">
        <div className="max-w-md w-full text-center">
          <div className="text-8xl mb-6" role="img" aria-label="checkmark">✅</div>

          <h1 className="text-3xl font-black text-gray-900 mb-3">
            {wasQueued ? 'Report Saved' : 'Help is on the way'}
          </h1>

          {wasQueued ? (
            <p className="text-lg text-gray-600 mb-4 leading-relaxed">
              You're offline. Your report has been saved on this device and will be sent
              automatically as soon as you have a signal.
            </p>
          ) : (
            <p className="text-lg text-gray-600 mb-4 leading-relaxed">
              Your report has been received. Emergency response teams are being
              notified and help is being coordinated to your location.
            </p>
          )}

          {reportId && (
            <div className="bg-gray-100 rounded-xl px-4 py-3 mb-6 inline-block">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Reference number</p>
              <p className="font-mono text-sm font-bold text-gray-800 break-all">{reportId}</p>
              <p className="text-xs text-gray-400 mt-1">Keep this for follow-up</p>
            </div>
          )}

          <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 mb-8 text-left">
            <p className="text-sm font-bold text-amber-800 mb-1">⚠ Stay safe</p>
            <ul className="text-sm text-amber-700 space-y-1 list-disc list-inside">
              <li>Move to higher ground if flooding</li>
              <li>Stay away from damaged buildings</li>
              <li>Call 112 for immediate life threat</li>
            </ul>
          </div>

          <button
            onClick={reset}
            className="w-full bg-red-600 hover:bg-red-700 active:bg-red-800
                       text-white text-lg font-bold py-4 rounded-2xl
                       transition-colors"
          >
            Submit Another Report
          </button>
        </div>
      </div>
    )
  }

  // ── form ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Page header ── */}
      <header className="bg-red-600 text-white px-5 pt-10 pb-6 safe-top">
        <h1 className="text-3xl font-black tracking-tight mb-1">🚨 Report Emergency</h1>
        <p className="text-red-100 text-base">
          Fill this form to alert rescue teams. Your report goes directly to responders.
        </p>
      </header>

      <main className="max-w-lg mx-auto px-4 py-6 space-y-5 pb-24">

        {/* ── Error banner ── */}
        {errorMsg && (
          <div className="bg-red-50 border border-red-300 rounded-2xl px-4 py-3
                          text-red-700 text-base font-medium">
            ⚠ {errorMsg}
          </div>
        )}

        {/* ── 1. Language ── */}
        <Card>
          <SectionTitle step="1">Language / भाषा</SectionTitle>
          <div className="grid grid-cols-4 gap-2">
            {LANGUAGES.map(l => (
              <button
                key={l.code}
                type="button"
                onClick={() => setLanguage(l.code)}
                disabled={isSubmitting}
                className={`py-2.5 px-1 rounded-xl text-sm font-semibold border-2 transition-all
                            disabled:opacity-40
                            ${language === l.code
                              ? 'bg-red-600 text-white border-red-600'
                              : 'bg-white text-gray-700 border-gray-200 hover:border-red-300'
                            }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </Card>

        {/* ── 2. Location ── */}
        <Card>
          <SectionTitle step="2">Your Location</SectionTitle>

          {/* GPS button */}
          <button
            type="button"
            onClick={requestGPS}
            disabled={isSubmitting || locState === 'loading'}
            className={`w-full flex items-center justify-center gap-3 py-4 rounded-2xl
                        text-base font-bold border-2 transition-all mb-3
                        disabled:opacity-50 disabled:cursor-not-allowed
                        ${locState === 'done'
                          ? 'bg-green-50 border-green-400 text-green-700'
                          : locState === 'denied'
                          ? 'bg-red-50 border-red-300 text-red-700'
                          : 'bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100'
                        }`}
          >
            {locState === 'loading' && (
              <span className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            )}
            {locState === 'done'    && <span className="text-xl">✅</span>}
            {locState === 'denied'  && <span className="text-xl">❌</span>}
            {locState === 'idle'    && <span className="text-xl">📍</span>}

            {locState === 'loading' && 'Getting your location…'}
            {locState === 'done'    && `Location found (${latitude?.toFixed(4)}, ${longitude?.toFixed(4)})`}
            {locState === 'denied'  && 'Location denied — type it below'}
            {locState === 'idle'    && '📍 Use My Location (GPS)'}
          </button>

          {/* Manual location text */}
          <div>
            <label className="block text-sm font-semibold text-gray-600 mb-1.5">
              Or describe your location
            </label>
            <input
              type="text"
              value={locationText}
              onChange={e => setLocationText(e.target.value)}
              placeholder="e.g. Near Jalpaiguri bridge, West Bengal"
              disabled={isSubmitting}
              className="w-full text-base border-2 border-gray-200 rounded-xl px-4 py-3
                         focus:outline-none focus:border-red-400
                         disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
          </div>
        </Card>

        {/* ── 3. Disaster type ── */}
        <Card>
          <SectionTitle step="3">What is happening?</SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            {DISASTER_TYPES.map(d => (
              <button
                key={d.value}
                type="button"
                onClick={() => setDisasterType(d.value)}
                disabled={isSubmitting}
                className={`flex flex-col items-center justify-center gap-1.5
                            py-5 rounded-2xl border-2 text-center
                            transition-all disabled:opacity-40
                            ${disasterType === d.value
                              ? 'bg-red-600 border-red-600 text-white shadow-lg scale-[1.03]'
                              : 'bg-white border-gray-200 text-gray-700 hover:border-red-300 hover:bg-red-50'
                            }`}
              >
                <span className="text-4xl leading-none">{d.emoji}</span>
                <span className="text-base font-bold">{d.label}</span>
                <span className="text-xs opacity-70">{d.labelHi}</span>
              </button>
            ))}
          </div>
        </Card>

        {/* ── 4. Description + voice ── */}
        <Card>
          <SectionTitle step="4">Describe what happened</SectionTitle>

          {/* Voice recording button */}
          <div className="mb-3">
            <VoiceWidget
              language={language}
              onTranscript={appendTranscript}
              disabled={isSubmitting}
            />
          </div>

          {/* Text area */}
          <div>
            <label className="block text-sm font-semibold text-gray-600 mb-1.5">
              Type your message
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Describe the emergency — what you see, how many people need help, any injuries…"
              disabled={isSubmitting}
              className="w-full text-base border-2 border-gray-200 rounded-xl px-4 py-3
                         focus:outline-none focus:border-red-400 resize-none
                         disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
          </div>
        </Card>

        {/* ── 5. Number of people ── */}
        <Card>
          <SectionTitle step="5">How many people need help?</SectionTitle>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setNumPeople(p => String(Math.max(0, (parseInt(p) || 0) - 1)))}
              disabled={isSubmitting || !numPeople || parseInt(numPeople) <= 0}
              aria-label="Decrease"
              className="w-14 h-14 rounded-2xl bg-gray-100 text-2xl font-bold
                         text-gray-700 hover:bg-gray-200 disabled:opacity-30
                         transition-colors flex items-center justify-center"
            >
              −
            </button>
            <input
              type="number"
              inputMode="numeric"
              min="0"
              value={numPeople}
              onChange={e => setNumPeople(e.target.value)}
              placeholder="0"
              disabled={isSubmitting}
              className="flex-1 text-center text-3xl font-black border-2 border-gray-200
                         rounded-2xl py-3 focus:outline-none focus:border-red-400
                         disabled:bg-gray-100"
            />
            <button
              type="button"
              onClick={() => setNumPeople(p => String((parseInt(p) || 0) + 1))}
              disabled={isSubmitting}
              aria-label="Increase"
              className="w-14 h-14 rounded-2xl bg-gray-100 text-2xl font-bold
                         text-gray-700 hover:bg-gray-200 disabled:opacity-30
                         transition-colors flex items-center justify-center"
            >
              +
            </button>
          </div>
          <p className="text-sm text-gray-400 mt-2 text-center">
            Include everyone — even if unsure, estimate
          </p>
        </Card>

        {/* ── 6. Vulnerable people ── */}
        <Card>
          <SectionTitle step="6">Is anyone in this group?</SectionTitle>
          <p className="text-sm text-gray-500 mb-3 -mt-1">Select all that apply</p>
          <div className="space-y-2">
            {VULNERABLE_OPTIONS.map(opt => {
              const checked = vulnerable.has(opt.value)
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleVulnerable(opt.value)}
                  disabled={isSubmitting}
                  className={`w-full flex items-center gap-4 py-4 px-4 rounded-2xl
                              border-2 text-left transition-all
                              disabled:opacity-40
                              ${checked
                                ? 'bg-red-50 border-red-400 text-red-800'
                                : 'bg-white border-gray-200 text-gray-700 hover:border-red-200'
                              }`}
                >
                  <span className="text-3xl leading-none shrink-0">{opt.emoji}</span>
                  <span className="text-base font-semibold flex-1">{opt.label}</span>
                  <span className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center shrink-0
                                    ${checked ? 'bg-red-600 border-red-600' : 'border-gray-300'}`}>
                    {checked && (
                      <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24"
                           stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </span>
                </button>
              )
            })}
          </div>
        </Card>

        {/* ── 7. Phone (optional) ── */}
        <Card>
          <SectionTitle step="7">Your phone number (optional)</SectionTitle>
          <input
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="+91 98765 43210"
            disabled={isSubmitting}
            className="w-full text-lg border-2 border-gray-200 rounded-xl px-4 py-3
                       focus:outline-none focus:border-red-400
                       disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-gray-400 mt-2">
            So rescue teams can call you back. Will not be shared publicly.
          </p>
        </Card>

        {/* ── Submit ── */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="w-full bg-red-600 hover:bg-red-700 active:bg-red-800
                     text-white text-xl font-black py-5 rounded-2xl shadow-lg
                     transition-colors disabled:opacity-60 disabled:cursor-not-allowed
                     flex items-center justify-center gap-3"
        >
          {isSubmitting ? (
            <>
              <span className="w-6 h-6 border-3 border-white border-t-transparent
                               rounded-full animate-spin shrink-0" />
              Sending…
            </>
          ) : (
            '🆘 Send for Help'
          )}
        </button>

        {/* Offline notice */}
        <p className="text-center text-xs text-gray-400 pb-4">
          No internet? Your report will be saved and sent automatically when you're back online.
        </p>

      </main>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Inline icons (no extra library)
// ---------------------------------------------------------------------------
function MicIcon({ className = 'w-5 h-5' }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} viewBox="0 0 24 24"
         fill="none" stroke="currentColor" strokeWidth={2}
         strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8"  y1="23" x2="16" y2="23"/>
    </svg>
  )
}

function StopIcon({ className = 'w-5 h-5' }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={className} viewBox="0 0 24 24"
         fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2"/>
    </svg>
  )
}
