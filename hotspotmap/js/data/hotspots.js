// ============================================================
// SmartShield — Hotspot Data Module
// Replace fetchHotspotData() internals with API call when ready
// ============================================================

const HOTSPOT_DATA = [
  {
    lat: 30.3165,
    lng: 78.0322,
    city: "Dehradun",
    risk: "high",
    reports: 18,
    incident: "Suspicious banking link detected",
  },
  {
    lat: 29.9457,
    lng: 78.1642,
    city: "Haridwar",
    risk: "medium",
    reports: 10,
    incident: "OTP scam attempt reported",
  },
  {
    lat: 30.0869,
    lng: 78.2676,
    city: "Rishikesh",
    risk: "high",
    reports: 14,
    incident: "Fake job offer link circulating",
  },
  {
    lat: 29.2183,
    lng: 79.513,
    city: "Haldwani",
    risk: "low",
    reports: 5,
    incident: "Phishing email cluster identified",
  },
  {
    lat: 30.7352,
    lng: 79.0669,
    city: "Uttarkashi",
    risk: "medium",
    reports: 8,
    incident: "Fake KYC update SMS wave",
  },
  {
    lat: 29.3803,
    lng: 79.4636,
    city: "Nainital",
    risk: "low",
    reports: 6,
    incident: "Spoofed government portal detected",
  },
  {
    lat: 29.8543,
    lng: 80.0915,
    city: "Pithoragarh",
    risk: "medium",
    reports: 9,
    incident: "Credential harvesting site flagged",
  },
];

const RECENT_INCIDENTS = [
  {
    city: "Dehradun",
    text: "Suspicious banking link — 3 min ago",
    risk: "high",
  },
  {
    city: "Haridwar",
    text: "OTP scam attempt — 12 min ago",
    risk: "medium",
  },
  {
    city: "Rishikesh",
    text: "Fake job offer link — 28 min ago",
    risk: "high",
  },
  {
    city: "Nainital",
    text: "Spoofed govt portal — 1 hr ago",
    risk: "low",
  },
  {
    city: "Uttarkashi",
    text: "Fake KYC SMS wave — 2 hr ago",
    risk: "medium",
  },
];

/**
 * Fetch hotspot data from API (protected).
 * Falls back to hardcoded data if API is unavailable.
 */
async function fetchHotspotData() {
  const token = localStorage.getItem("smartshield_token");

  try {
    const res = await fetch("/api/hotspots", {
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
        "Content-Type": "application/json",
      },
    });

    if (res.status === 401) {
      // Token expired or invalid — redirect to login
      localStorage.removeItem("smartshield_token");
      localStorage.removeItem("smartshield_user");
      window.location.href = "/login";
      return [];
    }

    const data = await res.json();
    if (data.success) return data.data;
  } catch (err) {
    console.warn("API unavailable, using local data:", err.message);
  }

  // Fallback to hardcoded data
  return HOTSPOT_DATA;
}

function getRecentIncidents() {
  return RECENT_INCIDENTS;
}
