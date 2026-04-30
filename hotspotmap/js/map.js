// ============================================================
// SmartShield — Map Module
// Handles Leaflet map init, markers, heatmap
// ============================================================

const RISK_COLORS = {
  high: "#ff3b3b",
  medium: "#ffc857",
  low: "#00ffa3",
};

const RISK_RADIUS = {
  high: 16,
  medium: 11,
  low: 7,
};

/**
 * Initialize Leaflet map centered on Uttarakhand.
 */
function initMap() {
  const map = L.map("map", {
    center: [30.0668, 79.0193],
    zoom: 7,
    zoomControl: false,
    attributionControl: true,
  });

  // CartoDB Dark Matter tiles
  L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }
  ).addTo(map);

  // Zoom control on bottom-right
  L.control.zoom({ position: "bottomright" }).addTo(map);

  return map;
}

/**
 * Create a custom pulsing HTML marker.
 */
function createPulseIcon(risk) {
  const color = RISK_COLORS[risk] || RISK_COLORS.low;
  return L.divIcon({
    className: "",
    iconSize: [60, 60],
    iconAnchor: [30, 30],
    popupAnchor: [0, -20],
    html: `
      <div class="custom-marker">
        <div class="pulse-ring ${risk}"></div>
        <div class="marker-dot ${risk}"></div>
      </div>
    `,
  });
}

/**
 * Build popup HTML for a hotspot.
 */
function buildPopupHTML(spot) {
  return `
    <div class="popup-inner">
      <div class="popup-city">${spot.city}</div>
      <span class="popup-risk ${spot.risk}">${spot.risk} risk</span>
      <div class="popup-reports">
        <strong>${spot.reports}</strong> phishing reports detected
      </div>
      <div class="popup-ai">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        AI detected phishing activity in this region
      </div>
    </div>
  `;
}

/**
 * Add hotspot markers to the map.
 * Returns the marker layer group.
 */
function addHotspots(map, data) {
  const markers = [];

  data.forEach((spot) => {
    // Circle marker (for the glow underlay)
    const circle = L.circleMarker([spot.lat, spot.lng], {
      radius: RISK_RADIUS[spot.risk] || 8,
      fillColor: RISK_COLORS[spot.risk] || RISK_COLORS.low,
      fillOpacity: 0.18,
      color: RISK_COLORS[spot.risk] || RISK_COLORS.low,
      weight: 1,
      opacity: 0.3,
    }).addTo(map);

    // Custom pulsing marker on top
    const marker = L.marker([spot.lat, spot.lng], {
      icon: createPulseIcon(spot.risk),
    }).addTo(map);

    // Popup
    marker.bindPopup(buildPopupHTML(spot), {
      maxWidth: 260,
      closeButton: false,
      className: "",
    });

    // Click → zoom
    marker.on("click", () => {
      map.flyTo([spot.lat, spot.lng], 10, { duration: 0.8 });
    });

    markers.push({ circle, marker, data: spot });
  });

  return markers;
}

/**
 * Initialize heatmap layer if leaflet-heat is available.
 * Returns the layer so it can be toggled.
 */
function initHeatmap(map, data) {
  if (typeof L.heatLayer !== "function") {
    console.warn("leaflet.heat not loaded — heatmap disabled");
    return null;
  }

  const heatData = data.map((s) => [s.lat, s.lng, s.reports / 18]); // normalized

  const heat = L.heatLayer(heatData, {
    radius: 40,
    blur: 30,
    maxZoom: 12,
    max: 1.0,
    gradient: {
      0.2: "#00ffa3",
      0.5: "#ffc857",
      0.8: "#ff3b3b",
      1.0: "#ff0000",
    },
  });

  return heat;
}
