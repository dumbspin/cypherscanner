import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { fetchHotspots, ReportLocation } from "../api/hotspots";

const markerIcon = L.icon({
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const MapView: React.FC = () => {
  const [reports, setReports] = useState<ReportLocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHotspots()
      .then((items) => setReports(items))
      .finally(() => setLoading(false));
  }, []);

  const center: [number, number] =
    reports.length > 0
      ? [reports[0].lat, reports[0].lng]
      : [30.3165, 78.0322]; // Uttarakhand fallback

  return (
    <div id="map" style={{ height: "100vh", width: "100%" }}>
      <MapContainer center={center} zoom={7} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {!loading &&
          reports.map((r, idx) => (
            <Marker
              key={`${r.incident}-${idx}`}
              position={[r.lat, r.lng]}
              icon={markerIcon}
            >
              <Popup>
                <div style={{ maxWidth: 220 }}>
                  <strong>{r.city || "Unknown"}</strong>
                  <div style={{ fontSize: "0.8rem" }}>
                    {r.reports} reports • {r.risk} risk
                  </div>
                  <a
                    href={r.incident}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: "0.8rem", wordBreak: "break-all" }}
                  >
                    {r.incident}
                  </a>
                </div>
              </Popup>
            </Marker>
          ))}
      </MapContainer>
    </div>
  );
};

export default MapView;

