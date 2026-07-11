/**
 * Mock data for the RescueAI dashboard.
 *
 * USE_MOCK flag
 * -------------
 * Set USE_MOCK = true  → all API calls are replaced by this static data.
 * Set USE_MOCK = false → live backend at http://localhost:8000 is used.
 *
 * Switch to false once the real /api/reports and /api/stats/summary
 * endpoints are confirmed working.
 */
export const USE_MOCK = false

// ---------------------------------------------------------------------------
// Shape mirrors GET /api/reports  (enriched — includes fields from GET /api/reports/{id})
// ---------------------------------------------------------------------------
export const MOCK_REPORTS = [
  {
    id: "r-001",
    source: "sms",
    raw_text: "Flood near Jalpaiguri bridge. 35 people stranded including elderly.",
    language: "en",
    translated_text: null,
    disaster_type: "flood",
    urgency_score: 91,
    status: "new",
    assigned_team: null,
    num_people: 35,
    vulnerable_flags: ["elderly"],
    verification_status: "weather_confirmed",
    corroboration_count: 3,
    is_duplicate_of: null,
    location: { latitude: 26.5159, longitude: 88.7180, text: "Jalpaiguri Bridge" },
    urgency: {
      score: 91,
      breakdown: {
        final_score: 91,
        base_score: 76,
        factors: {
          people:        { score: 23, explanation: "35 people (log scale)" },
          vulnerable:    { score: 15, explanation: "1 vulnerable group: elderly (+15)" },
          verification:  { score: 20, explanation: "Weather data confirms (+20)" },
          corroboration: { score: 15, explanation: "3 corroborating reports (+15)" },
          time_decay:    { score: 3,  explanation: "Report 0.6h old, no decay" },
        },
        multiplier: { value: 1.0, explanation: "Flood: More warning time (×1.0)" },
        summary: "CRITICAL urgency driven by people affected and verification",
      },
    },
    created_at: new Date(Date.now() - 38 * 60000).toISOString(),
    updated_at: new Date(Date.now() - 12 * 60000).toISOString(),
  },
  {
    id: "r-002",
    source: "whatsapp",
    raw_text: "Earthquake tremors in Sikkim. Buildings damaged. Family of 6 trapped, baby inside.",
    language: "en",
    translated_text: null,
    disaster_type: "earthquake",
    urgency_score: 87,
    status: "in_progress",
    assigned_team: "NDRF Alpha Team",
    num_people: 6,
    vulnerable_flags: ["child"],
    verification_status: "satellite_confirmed",
    corroboration_count: 1,
    is_duplicate_of: null,
    location: { latitude: 27.3389, longitude: 88.6065, text: "Gangtok, Sikkim" },
    urgency: {
      score: 87,
      breakdown: {
        final_score: 87,
        base_score: 72.5,
        factors: {
          people:        { score: 17.8, explanation: "6 people (log scale)" },
          vulnerable:    { score: 15,   explanation: "1 vulnerable group: child (+15)" },
          verification:  { score: 25,   explanation: "Satellite data confirms (+25)" },
          corroboration: { score: 5,    explanation: "1 corroborating report (+5)" },
          time_decay:    { score: 9.7,  explanation: "Report 3.9h old (+9.7)" },
        },
        multiplier: { value: 1.2, explanation: "Earthquake: Minimal warning time (×1.2)" },
        summary: "CRITICAL urgency driven by satellite verification and vulnerable populations",
      },
    },
    created_at: new Date(Date.now() - 230 * 60000).toISOString(),
    updated_at: new Date(Date.now() - 45 * 60000).toISOString(),
  },
  {
    id: "r-003",
    source: "app",
    raw_text: "Cyclone making landfall near Digha coast. Entire village evacuating. 200 residents, pregnant woman needs ambulance.",
    language: "en",
    translated_text: null,
    disaster_type: "cyclone",
    urgency_score: 84,
    status: "new",
    assigned_team: null,
    num_people: 200,
    vulnerable_flags: ["pregnant"],
    verification_status: "satellite_confirmed",
    corroboration_count: 5,
    is_duplicate_of: null,
    location: { latitude: 21.6267, longitude: 87.5388, text: "Digha Coast, WB" },
    urgency: {
      score: 84,
      breakdown: {
        final_score: 84,
        base_score: 76.4,
        factors: {
          people:        { score: 28.3, explanation: "200 people (log scale)" },
          vulnerable:    { score: 15,   explanation: "1 vulnerable group: pregnant (+15)" },
          verification:  { score: 25,   explanation: "Satellite data confirms (+25)" },
          corroboration: { score: 20,   explanation: "5+ corroborating reports (capped, +20)" },
          time_decay:    { score: 0,    explanation: "Recent report, no decay" },
        },
        multiplier: { value: 1.1, explanation: "Cyclone: Limited warning time (×1.1)" },
        summary: "CRITICAL urgency driven by people affected and satellite verification",
      },
    },
    created_at: new Date(Date.now() - 15 * 60000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 60000).toISOString(),
  },
  {
    id: "r-004",
    source: "voice",
    raw_text: "Flooding in low-lying areas near Kaziranga. 12 families displaced. Old man wheelchair user cannot move.",
    language: "en",
    translated_text: null,
    disaster_type: "flood",
    urgency_score: 72,
    status: "new",
    assigned_team: null,
    num_people: 48,
    vulnerable_flags: ["elderly", "disabled"],
    verification_status: "corroborated",
    corroboration_count: 2,
    is_duplicate_of: null,
    location: { latitude: 26.5775, longitude: 93.1721, text: "Kaziranga, Assam" },
    urgency: {
      score: 72,
      breakdown: {
        final_score: 72,
        base_score: 72,
        factors: {
          people:        { score: 24.7, explanation: "48 people (log scale)" },
          vulnerable:    { score: 30,   explanation: "2 vulnerable groups: elderly, disabled (+30)" },
          verification:  { score: 10,   explanation: "Corroborated by multiple reports (+10)" },
          corroboration: { score: 10,   explanation: "2 corroborating reports (+10)" },
          time_decay:    { score: 0,    explanation: "Recent report, no decay" },
        },
        multiplier: { value: 1.0, explanation: "Flood: More warning time (×1.0)" },
        summary: "HIGH urgency driven by vulnerable populations",
      },
    },
    created_at: new Date(Date.now() - 55 * 60000).toISOString(),
    updated_at: new Date(Date.now() - 20 * 60000).toISOString(),
  },
  {
    id: "r-005",
    source: "sms",
    raw_text: "River embankment breach in Malda. Water entering homes. 8 people including 2 children.",
    language: "en",
    translated_text: null,
    disaster_type: "flood",
    urgency_score: 58,
    status: "new",
    assigned_team: null,
    num_people: 8,
    vulnerable_flags: ["child"],
    verification_status: "unverified",
    corroboration_count: 0,
    is_duplicate_of: null,
    location: { latitude: 25.0108, longitude: 88.1415, text: "Malda, WB" },
    urgency: {
      score: 58,
      breakdown: {
        final_score: 58,
        base_score: 58,
        factors: {
          people:        { score: 19.1, explanation: "8 people (log scale)" },
          vulnerable:    { score: 15,   explanation: "1 vulnerable group: child (+15)" },
          verification:  { score: 0,    explanation: "Unverified" },
          corroboration: { score: 0,    explanation: "Single report, no corroboration" },
          time_decay:    { score: 24,   explanation: "Report 6.8h old (+24)" },
        },
        multiplier: { value: 1.0, explanation: "Flood: More warning time (×1.0)" },
        summary: "MEDIUM urgency driven by vulnerable populations and time waiting",
      },
    },
    created_at: new Date(Date.now() - 408 * 60000).toISOString(),
    updated_at: new Date(Date.now() - 408 * 60000).toISOString(),
  },
  {
    id: "r-006",
    source: "app",
    raw_text: "Minor earthquake tremors felt. No damage visible. Reporting for awareness.",
    language: "en",
    translated_text: null,
    disaster_type: "earthquake",
    urgency_score: 12,
    status: "new",
    assigned_team: null,
    num_people: null,
    vulnerable_flags: [],
    verification_status: "unverified",
    corroboration_count: 0,
    is_duplicate_of: null,
    location: { latitude: 27.0974, longitude: 88.2663, text: "Darjeeling, WB" },
    urgency: {
      score: 12,
      breakdown: {
        final_score: 12,
        base_score: 10,
        factors: {
          people:        { score: 0,  explanation: "No people count provided" },
          vulnerable:    { score: 0,  explanation: "No vulnerable populations identified" },
          verification:  { score: 0,  explanation: "Unverified" },
          corroboration: { score: 0,  explanation: "Single report, no corroboration" },
          time_decay:    { score: 10, explanation: "Report 2.1h old (+10)" },
        },
        multiplier: { value: 1.2, explanation: "Earthquake: Minimal warning time (×1.2)" },
        summary: "LOW urgency — single unverified report, no people count",
      },
    },
    created_at: new Date(Date.now() - 127 * 60000).toISOString(),
    updated_at: new Date(Date.now() - 127 * 60000).toISOString(),
  },
]

// ---------------------------------------------------------------------------
// Shape mirrors GET /api/stats/summary
// ---------------------------------------------------------------------------
export const MOCK_SUMMARY = {
  reports: {
    total:      40,
    active:     24,
    critical:   3,
    unverified: 9,
    by_type: {
      flood:      14,
      earthquake:  6,
      cyclone:     3,
      other:       1,
    },
    by_verification: {
      unverified:          9,
      corroborated:        5,
      weather_confirmed:   4,
      satellite_confirmed: 6,
    },
  },
  teams: {
    total:     12,
    available:  7,
    deployed:   5,
  },
}

// ---------------------------------------------------------------------------
// Mock dispatch recommendations shape (mirrors GET /api/reports/{id}/recommend-dispatch)
// ---------------------------------------------------------------------------
export const MOCK_DISPATCH = {
  "r-001": {
    recommendations: [
      { team_id: "t-1", team_name: "NDRF Alpha Team",    team_type: "NDRF",      capacity: 20, distance_km: 4.2,  eta_estimate: "~7 min"  },
      { team_id: "t-2", team_name: "SDRF Bravo Unit",    team_type: "SDRF",      capacity: 15, distance_km: 8.1,  eta_estimate: "~13 min" },
      { team_id: "t-3", team_name: "NGO Relief Corps",   team_type: "NGO",       capacity: 10, distance_km: 12.5, eta_estimate: "~20 min" },
    ],
  },
  "r-002": {
    recommendations: [
      { team_id: "t-4", team_name: "NDRF Charlie Team",  team_type: "NDRF",      capacity: 25, distance_km: 2.9,  eta_estimate: "~5 min"  },
    ],
  },
  "r-003": {
    recommendations: [
      { team_id: "t-5", team_name: "SDRF Delta Unit",    team_type: "SDRF",      capacity: 20, distance_km: 6.7,  eta_estimate: "~11 min" },
      { team_id: "t-6", team_name: "Volunteer Squad 1",  team_type: "volunteer", capacity: 8,  distance_km: 9.3,  eta_estimate: "~15 min" },
    ],
  },
}
