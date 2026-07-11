import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// ---------------------------------------------------------------------------
// Service worker registration (PWA — full app)
// Enables offline support and Add to Home Screen on mobile devices
// ---------------------------------------------------------------------------
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then(reg => {
        console.log('[PWA] Service worker registered, scope:', reg.scope)
        
        // Check for updates periodically
        setInterval(() => {
          reg.update()
        }, 60000) // Check every minute
      })
      .catch(err => {
        console.warn('[PWA] Service worker registration failed:', err)
      })
  })
}
