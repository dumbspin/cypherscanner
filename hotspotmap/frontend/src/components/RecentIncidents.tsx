import React from "react";

const RecentIncidents: React.FC = () => {
  return (
    <div className="overlay panel-bottom-left">
      <div className="glass-panel">
        <div className="incidents-header">
          <h3>Recent Incidents</h3>
          <span className="incidents-count">LIVE</span>
        </div>
        <div id="incident-list">
          {/* You can map over recent reports here if desired */}
        </div>
      </div>
    </div>
  );
};

export default RecentIncidents;

