import React from "react";

const FiltersPanel: React.FC = () => {
  return (
    <div className="overlay panel-top-right">
      <div className="glass-panel">
        <div className="filter-group">
          <div className="filter-label">Time Range</div>
          <div className="pill-row">
            <button className="pill active">24h</button>
            <button className="pill">7d</button>
            <button className="pill">30d</button>
          </div>
        </div>

        <div className="filter-group">
          <div className="filter-label">Attack Type</div>
          <div className="pill-row">
            <button className="pill active">All</button>
            <button className="pill">SMS</button>
            <button className="pill">Email</button>
            <button className="pill">URL</button>
          </div>
        </div>

        <div className="toggle-row">
          <div className="toggle-switch" id="heatmap-toggle" />
          <span className="toggle-label">Heatmap Layer</span>
        </div>
      </div>
    </div>
  );
};

export default FiltersPanel;

