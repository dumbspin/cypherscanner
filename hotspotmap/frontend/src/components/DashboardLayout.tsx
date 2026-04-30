import React, { useEffect } from "react";
import MapView from "./MapView";
import FiltersPanel from "./FiltersPanel";
import RecentIncidents from "./RecentIncidents";
import ReportModal from "./ReportModal";
import { logout } from "../api/auth";

const DashboardLayout: React.FC = () => {
  useEffect(() => {
    try {
      const userRaw = localStorage.getItem("smartshield_user");
      if (userRaw) {
        const user = JSON.parse(userRaw);
        const el = document.getElementById("user-greeting");
        if (el && user?.name) {
          el.textContent = `Welcome, ${user.name}`;
        }
      }
    } catch {
      // ignore
    }
  }, []);

  return (
    <>
      <MapView />

      {/* Top-left title & legend */}
      <div className="overlay panel-top-left">
        <div className="glass-panel panel-title">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "0.5rem",
            }}
          >
            <h1>
              SmartShield <span className="badge-ai">AI</span>
            </h1>
            <button
              id="btn-logout"
              style={{
                background: "rgba(255,59,59,0.12)",
                border: "1px solid rgba(255,59,59,0.2)",
                color: "#ff3b3b",
                fontSize: "0.65rem",
                padding: "0.3rem 0.7rem",
                borderRadius: "999px",
                cursor: "pointer",
                fontFamily: "Poppins, sans-serif",
                fontWeight: 500,
                transition: "0.3s",
              }}
              onClick={() => {
                localStorage.removeItem("smartshield_token");
                localStorage.removeItem("smartshield_user");
                logout().finally(() => window.location.reload());
              }}
            >
              Logout
            </button>
          </div>

          <p className="subtitle">
            Phishing Hotspot Intelligence — Uttarakhand
          </p>
          <p
            id="user-greeting"
            style={{
              fontSize: "0.68rem",
              color: "#8896ab",
              marginBottom: "0.4rem",
            }}
          ></p>

          <div className="live-indicator">
            <span className="live-dot"></span>
            Live Monitoring Active
          </div>

          <div className="legend">
            <div className="legend-item">
              <span className="legend-dot high"></span> High Risk
            </div>
            <div className="legend-item">
              <span className="legend-dot medium"></span> Medium Risk
            </div>
            <div className="legend-item">
              <span className="legend-dot low"></span> Low Risk
            </div>
          </div>
        </div>
      </div>

      <FiltersPanel />
      <RecentIncidents />
      <ReportModal />
    </>
  );
};

export default DashboardLayout;

