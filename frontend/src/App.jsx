import { useState, useEffect } from 'react'

function App() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Test API connection
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setHealthStatus(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('API connection failed:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-indigo-900 mb-4">
            🚨 RescueAI
          </h1>
          <p className="text-xl text-gray-700">
            Disaster Response Management System
          </p>
        </header>

        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-xl p-8 mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              System Status
            </h2>
            
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
              </div>
            ) : healthStatus ? (
              <div className="space-y-3">
                <div className="flex items-center">
                  <span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-3"></span>
                  <span className="text-gray-700">
                    Backend API: <span className="font-semibold text-green-600">Connected</span>
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  <p>Service: {healthStatus.service}</p>
                  <p>Status: {healthStatus.status}</p>
                  <p>Timestamp: {new Date(healthStatus.timestamp).toLocaleString()}</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center text-red-600">
                <span className="inline-block w-3 h-3 bg-red-500 rounded-full mr-3"></span>
                <span>Backend API: Disconnected</span>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              Welcome to RescueAI
            </h2>
            <div className="space-y-4 text-gray-700">
              <p>
                RescueAI is an intelligent disaster response management system designed to 
                help emergency response teams coordinate relief efforts effectively.
              </p>
              
              <div className="grid md:grid-cols-2 gap-4 mt-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-2">📊 Report Management</h3>
                  <p className="text-sm text-gray-600">
                    Track and manage disaster reports from multiple sources including SMS, WhatsApp, and mobile apps.
                  </p>
                </div>
                
                <div className="bg-green-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-green-900 mb-2">👥 Team Coordination</h3>
                  <p className="text-sm text-gray-600">
                    Coordinate NDRF, SDRF, NGO, and volunteer teams for efficient disaster response.
                  </p>
                </div>
                
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-yellow-900 mb-2">🎯 Priority Routing</h3>
                  <p className="text-sm text-gray-600">
                    Intelligent urgency scoring based on vulnerable populations and disaster severity.
                  </p>
                </div>
                
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-purple-900 mb-2">✅ Verification System</h3>
                  <p className="text-sm text-gray-600">
                    Multi-level verification including satellite and weather confirmation.
                  </p>
                </div>
              </div>

              <div className="mt-8 p-4 bg-indigo-50 rounded-lg border-l-4 border-indigo-600">
                <p className="text-sm font-semibold text-indigo-900 mb-2">
                  🚀 Getting Started
                </p>
                <ol className="text-sm text-gray-700 list-decimal list-inside space-y-1">
                  <li>Backend API is running on http://localhost:8000</li>
                  <li>Frontend dashboard is running on http://localhost:5173</li>
                  <li>Database has been seeded with 40 sample disaster reports</li>
                  <li>Start building your dashboard components!</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
