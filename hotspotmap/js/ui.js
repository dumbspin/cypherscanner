// ============================================================
// SmartShield — UI Module
// Handles filters, incidents list, report modal, heatmap toggle
// ============================================================

/**
 * Wire up filter pill active-state toggling.
 */
function initFilters() {
  document.querySelectorAll(".pill-row").forEach((row) => {
    const pills = row.querySelectorAll(".pill");
    pills.forEach((pill) => {
      pill.addEventListener("click", () => {
        // toggle within the group
        pills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
      });
    });
  });
}

/**
 * Populate the recent incidents list.
 */
function initIncidentList(incidents) {
  const container = document.getElementById("incident-list");
  if (!container) return;

  const riskIcons = {
    high: "⚠",
    medium: "⚡",
    low: "ℹ",
  };

  container.innerHTML = incidents
    .map(
      (inc) => `
      <div class="incident-item">
        <div class="incident-icon ${inc.risk}">${riskIcons[inc.risk] || "⚠"}</div>
        <div>
          <div class="incident-text">${inc.text}</div>
          <div class="incident-city">${inc.city}</div>
        </div>
      </div>
    `
    )
    .join("");
}

/**
 * Initialize heatmap toggle switch.
 */
function initHeatmapToggle(map, heatLayer) {
  const toggle = document.getElementById("heatmap-toggle");
  if (!toggle || !heatLayer) return;

  let isActive = false;

  toggle.addEventListener("click", () => {
    isActive = !isActive;
    toggle.classList.toggle("active", isActive);

    if (isActive) {
      heatLayer.addTo(map);
    } else {
      map.removeLayer(heatLayer);
    }
  });
}

/**
 * Initialize the Report Incident modal.
 */
function initReportModal() {
  const backdrop = document.getElementById("report-modal");
  const openBtn = document.getElementById("btn-report");
  const closeBtn = document.getElementById("modal-close");
  const form = document.getElementById("report-form");

  if (!backdrop || !openBtn) return;

  openBtn.addEventListener("click", () => {
    backdrop.classList.add("open");
  });

  // Close via button
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      backdrop.classList.remove("open");
    });
  }

  // Close on backdrop click
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) {
      backdrop.classList.remove("open");
    }
  });

  // ESC key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      backdrop.classList.remove("open");
    }
  });

  // Submit
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      console.log("📢 Incident Report Submitted:", data);
      console.table(data);

      // Show quick confirmation
      const btn = form.querySelector(".btn-submit");
      const origText = btn.textContent;
      btn.textContent = "✓ Submitted!";
      btn.style.background = "linear-gradient(135deg, #00ffa3, #00cc82)";

      setTimeout(() => {
        btn.textContent = origText;
        btn.style.background = "";
        form.reset();
        backdrop.classList.remove("open");
      }, 1500);
    });
  }
}
