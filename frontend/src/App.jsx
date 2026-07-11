import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import HowItWorks     from './components/HowItWorks'
import CommandCenter  from './components/CommandCenter'
import AIInsights     from './components/AIInsights'
import IncidentDetail from './components/IncidentDetail'
import CitizenReport  from './components/CitizenReport'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing page - How It Works */}
        <Route path="/" element={<HowItWorks />} />

        {/* Main dashboard */}
        <Route path="/command-center" element={<CommandCenter />} />

        {/* AI Insights */}
        <Route path="/insights" element={<AIInsights />} />

        {/* Full incident detail view */}
        <Route path="/incident/:id" element={<IncidentDetail />} />

        {/* Citizen PWA reporting form */}
        <Route path="/report" element={<CitizenReport />} />

        {/* Catch-all → landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
