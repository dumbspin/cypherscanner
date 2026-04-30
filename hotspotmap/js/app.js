// ============================================================
// SmartShield — App Entry Point
// Orchestrates map, data, and UI initialization
// ============================================================

(async function SmartShieldApp() {
  // 1. Init map
  const map = initMap();

  // 2. Fetch hotspot data
  const hotspots = await fetchHotspotData();

  // 3. Add markers
  addHotspots(map, hotspots);

  // 4. Init heatmap (hidden by default)
  const heatLayer = initHeatmap(map, hotspots);

  // 5. Init UI
  initFilters();
  initIncidentList(getRecentIncidents());
  initHeatmapToggle(map, heatLayer);
  initReportModal();

  console.log(
    "%c🛡 SmartShield Dashboard Initialized",
    "color: #00ffa3; font-size: 14px; font-weight: bold;"
  );
  console.log(`   ${hotspots.length} hotspots loaded`);
})();
