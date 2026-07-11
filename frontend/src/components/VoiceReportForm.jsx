/**
 * VoiceReportForm
 *
 * Lets a field worker submit a disaster report by speaking into the mic.
 * Transcription happens entirely in the browser via the Web Speech API —
 * zero API keys, zero cost, works offline (Chrome uses local models when
 * available, falls back to Google's free on-device API otherwise).
 *
 * Browser support note
 * --------------------
 * The Web Speech API is fully supported in Chrome/Edge (desktop + Android).
 * Firefox and Safari have partial or no support.  A plain-text fallback
 * input is shown whenever the API is unavailable so the form always works.
 *
 * Supported languages (extend LANGUAGES array to add more)
 * ---------------------------------------------------------
 * en-IN  English (India)
 * en-US  English (US)
 * hi-IN  Hindi
 * bn-IN  Bengali
 * ta-IN  Tamil
 * te-IN  Telugu
 */

import { useState, useEffect, useRef, useCallback } from 'react'

// ---------------------------------------------------------------------------
// Language options
// ---------------------------------------------------------------------------
const LANGUAGES = [
  { code: 'en-IN', label: 'English (India)' },
  { code: 'en-US', label: 'English (US)' },
  { code: 'hi-IN', label: 'हिन्दी — Hindi' },
  { code: 'bn-IN', label: 'বাংলা — Bengali' },
  { code: 'ta-IN', label: 'தமிழ் — Tamil' },
  { code: 'te-IN', label: 'తెలుగు — Telugu' },
]

// ---------------------------------------------------------------------------
// Recording states (simple state-machine)
// ---------------------------------------------------------------------------
const STATE = {
  IDLE:        'idle',        // nothing happening
  LISTENING:   'listening',   // mic open, transcribing
  SUBMITTING:  'submitting',  // POST in-flight
  SUCCESS:     'success',     // report saved
  ERROR:       'error',       // submission or browser error
}

// ---------------------------------------------------------------------------
// Detect Web Speech API availability once on module load
// ---------------------------------------------------------------------------
const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null

const SPEECH_SUPPORTED = Boolean(SpeechRecognition)

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function VoiceReportForm() {
  const [recState,      setRecState]      = useState(STATE.IDLE)
  const [language,      setLanguage]      = useState('en-IN')
  const [transcript,    setTranscript]    = useState('')  // confirmed final text
  const [interim,       setInterim]       = useState('')  // live partial text
  const [errorMsg,      setErrorMsg]      = useState('')
  const [reportId,      setReportId]      = useState(null)
  const [useFallback,   setUseFallback]   = useState(!SPEECH_SUPPORTED)

  // Optional location fields
  const [latitude,      setLatitude]      = useState('')
  const [longitude,     setLongitude]     = useState('')
  const [locationText,  setLocationText]  = useState('')
  const [phone,         setPhone]         = useState('')

  const recognitionRef = useRef(null)

  // ── cleanup on unmount ──────────────────────────────────────────────────
  useEffect(() => {
    return () => { recognitionRef.current?.abort() }
  }, [])

  // ── start recording ─────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    setErrorMsg('')
    setTranscript('')
    setInterim('')
    setReportId(null)

    const recognition = new SpeechRecognition()
    recognition.lang           = language
    recognition.interimResults = true   // stream partial results for live feedback
    recognition.maxAlternatives = 1
    recognition.continuous     = true   // keep mic open until user stops

    recognition.onresult = (event) => {
      let finalText   = ''
      let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript
        if (event.results[i].isFinal) finalText   += t + ' '
        else                          interimText += t
      }
      if (finalText)   setTranscript(prev => prev + finalText)
      if (interimText) setInterim(interimText)
    }

    recognition.onerror = (event) => {
      // 'no-speech' and 'aborted' are non-critical — don't show as errors
      if (event.error === 'no-speech' || event.error === 'aborted') return
      setErrorMsg(`Microphone error: ${event.error}. Try using Chrome, or use the text fallback below.`)
      setRecState(STATE.ERROR)
    }

    recognition.onend = () => {
      // Clear interim when mic closes
      setInterim('')
      // Only transition back to IDLE if we're still in LISTENING state
      // (submit() sets SUBMITTING before stop() fires onend)
      setRecState(prev => prev === STATE.LISTENING ? STATE.IDLE : prev)
    }

    recognitionRef.current = recognition
    recognition.start()
    setRecState(STATE.LISTENING)
  }, [language])

  // ── stop recording ──────────────────────────────────────────────────────
  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
    setRecState(STATE.IDLE)
  }, [])

  // ── submit report ────────────────────────────────────────────────────────
  const submitReport = useCallback(async (rawText) => {
    if (!rawText.trim()) {
      setErrorMsg('Please record or type a message before submitting.')
      return
    }

    // Stop mic if still open
    if (recState === STATE.LISTENING) {
      recognitionRef.current?.stop()
    }

    setRecState(STATE.SUBMITTING)
    setErrorMsg('')

    const body = {
      source:    'voice',
      raw_text:  rawText.trim(),
      reporter_phone:  phone.trim()   || null,
      latitude:        latitude       ? parseFloat(latitude)  : null,
      longitude:       longitude      ? parseFloat(longitude) : null,
      location_text:   locationText.trim() || null,
    }

    try {
      const res = await fetch('/api/reports/intake', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setReportId(data.report_id)
      setRecState(STATE.SUCCESS)
      // Clear the form fields on success
      setTranscript('')
      setPhone('')
      setLatitude('')
      setLongitude('')
      setLocationText('')
    } catch (err) {
      setErrorMsg(`Submission failed: ${err.message}`)
      setRecState(STATE.ERROR)
    }
  }, [recState, phone, latitude, longitude, locationText])

  // ── auto-fill GPS from browser ───────────────────────────────────────────
  const fillGPS = () => {
    if (!navigator.geolocation) {
      setErrorMsg('Geolocation is not supported by this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6))
        setLongitude(pos.coords.longitude.toFixed(6))
      },
      () => setErrorMsg('Location access denied. Enter coordinates manually.'),
    )
  }

  // ── reset ────────────────────────────────────────────────────────────────
  const reset = () => {
    recognitionRef.current?.abort()
    setRecState(STATE.IDLE)
    setTranscript('')
    setInterim('')
    setErrorMsg('')
    setReportId(null)
  }

  // ── derived helpers ──────────────────────────────────────────────────────
  const isListening  = recState === STATE.LISTENING
  const isSubmitting = recState === STATE.SUBMITTING
  const isSuccess    = recState === STATE.SUCCESS
  const displayText  = transcript + (interim ? interim : '')

  // ── render ───────────────────────────────────────────────────────────────
  return (
    <div className="bg-white rounded-lg shadow-xl p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-gray-800">
            🎙️ Voice Report
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Speak your report — it's transcribed instantly in the browser.
            No data sent to any transcription server.
          </p>
        </div>
        {/* Chrome notice */}
        {SPEECH_SUPPORTED && (
          <span className="hidden sm:block text-xs bg-yellow-50 border border-yellow-200 text-yellow-700 px-3 py-1 rounded-full">
            Works best in Chrome
          </span>
        )}
      </div>

      {/* Unsupported browser banner */}
      {!SPEECH_SUPPORTED && (
        <div className="mb-5 p-3 bg-amber-50 border border-amber-300 rounded-lg text-sm text-amber-800">
          <strong>Web Speech API not available in this browser.</strong>{' '}
          Please use Chrome or Edge for voice input, or type your report below.
        </div>
      )}

      {/* Success state */}
      {isSuccess && (
        <div className="mb-5 p-4 bg-green-50 border border-green-300 rounded-lg">
          <p className="text-green-800 font-semibold">
            ✅ Report submitted successfully!
          </p>
          <p className="text-sm text-green-700 mt-1">
            Report ID: <code className="bg-green-100 px-1 rounded">{reportId}</code>
          </p>
          <button
            onClick={reset}
            className="mt-3 text-sm text-green-700 underline hover:text-green-900"
          >
            Submit another report
          </button>
        </div>
      )}

      {/* Error banner */}
      {errorMsg && (
        <div className="mb-5 p-3 bg-red-50 border border-red-300 rounded-lg text-sm text-red-700">
          ⚠️ {errorMsg}
        </div>
      )}

      {!isSuccess && (
        <>
          {/* ── Language selector ── */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Language
            </label>
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              disabled={isListening || isSubmitting}
              className="w-full sm:w-64 border border-gray-300 rounded-md px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-500
                         disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              {LANGUAGES.map(l => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* ── Voice controls (shown when Speech API available and not in fallback mode) ── */}
          {SPEECH_SUPPORTED && !useFallback && (
            <div className="mb-5">
              <div className="flex items-center gap-3 mb-3">
                {!isListening ? (
                  <button
                    onClick={startListening}
                    disabled={isSubmitting}
                    className="flex items-center gap-2 bg-red-600 hover:bg-red-700
                               text-white font-semibold px-5 py-2.5 rounded-full
                               transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <MicIcon /> Record
                  </button>
                ) : (
                  <button
                    onClick={stopListening}
                    className="flex items-center gap-2 bg-gray-700 hover:bg-gray-800
                               text-white font-semibold px-5 py-2.5 rounded-full
                               transition-colors animate-pulse"
                  >
                    <StopIcon /> Stop Recording
                  </button>
                )}

                {isListening && (
                  <span className="flex items-center gap-1.5 text-sm text-red-600 font-medium">
                    <span className="inline-block w-2 h-2 bg-red-500 rounded-full animate-ping" />
                    Listening…
                  </span>
                )}
              </div>

              {/* Live transcript box */}
              <div
                className={`min-h-[100px] p-3 rounded-lg border text-sm font-mono
                            ${isListening
                              ? 'border-red-300 bg-red-50'
                              : 'border-gray-200 bg-gray-50'}`}
              >
                {displayText
                  ? (
                    <>
                      <span className="text-gray-800">{transcript}</span>
                      {interim && <span className="text-gray-400 italic">{interim}</span>}
                    </>
                  )
                  : (
                    <span className="text-gray-400 italic">
                      {isListening ? 'Start speaking…' : 'Transcript will appear here after recording.'}
                    </span>
                  )
                }
              </div>

              {/* Switch to text fallback */}
              <button
                onClick={() => setUseFallback(true)}
                className="mt-2 text-xs text-gray-400 hover:text-gray-600 underline"
              >
                Switch to text input instead
              </button>
            </div>
          )}

          {/* ── Text fallback ── */}
          {(useFallback || !SPEECH_SUPPORTED) && (
            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Report Text
                {SPEECH_SUPPORTED && (
                  <button
                    onClick={() => setUseFallback(false)}
                    className="ml-2 text-xs text-indigo-500 hover:text-indigo-700 underline font-normal"
                  >
                    Switch to voice input
                  </button>
                )}
              </label>
              <textarea
                rows={4}
                value={transcript}
                onChange={e => setTranscript(e.target.value)}
                placeholder="Type your disaster report here… e.g. 'Flood near the main bridge, 15 people stranded including elderly women.'"
                disabled={isSubmitting}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-indigo-500
                           disabled:bg-gray-100 disabled:cursor-not-allowed resize-none"
              />
            </div>
          )}

          {/* ── Optional location fields ── */}
          <details className="mb-5 group">
            <summary className="cursor-pointer text-sm font-medium text-gray-600
                                hover:text-gray-800 select-none list-none flex items-center gap-1">
              <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
              &nbsp;Add location (optional but improves dispatch accuracy)
            </summary>
            <div className="mt-3 grid sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Phone number</label>
                <input
                  type="tel"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="+91 98765 43210"
                  disabled={isSubmitting}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-500
                             disabled:bg-gray-100"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Location description</label>
                <input
                  type="text"
                  value={locationText}
                  onChange={e => setLocationText(e.target.value)}
                  placeholder="Near river bridge, Jalpaiguri"
                  disabled={isSubmitting}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-500
                             disabled:bg-gray-100"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Latitude</label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={e => setLatitude(e.target.value)}
                  placeholder="26.5159"
                  disabled={isSubmitting}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-500
                             disabled:bg-gray-100"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Longitude</label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={e => setLongitude(e.target.value)}
                  placeholder="26.7187"
                  disabled={isSubmitting}
                  className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-500
                             disabled:bg-gray-100"
                />
              </div>
              <div className="sm:col-span-2">
                <button
                  type="button"
                  onClick={fillGPS}
                  disabled={isSubmitting}
                  className="text-xs text-indigo-600 hover:text-indigo-800 underline
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  📍 Auto-fill my current GPS coordinates
                </button>
              </div>
            </div>
          </details>

          {/* ── Submit button ── */}
          <button
            onClick={() => submitReport(transcript)}
            disabled={isSubmitting || isListening || !transcript.trim()}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold
                       py-3 px-6 rounded-lg transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent
                                 rounded-full animate-spin" />
                Submitting…
              </>
            ) : (
              '📤 Submit Report'
            )}
          </button>

          {isListening && (
            <p className="mt-2 text-xs text-center text-gray-500">
              Stop recording first, then submit.
            </p>
          )}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tiny inline SVG icons (no icon library dependency)
// ---------------------------------------------------------------------------
function MicIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8"  y1="23" x2="16" y2="23"/>
    </svg>
  )
}

function StopIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24"
         fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2"/>
    </svg>
  )
}
