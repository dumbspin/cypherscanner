// ============================================================
// SmartShield — Hotspots API Route (Protected)
// ============================================================

const express = require("express");
const { protect } = require("../middleware/auth");
const Report = require("../models/Report");

const router = express.Router();

function riskFromCount(count) {
  if (count >= 10) return "high";
  if (count >= 4) return "medium";
  return "low";
}

/**
 * GET /api/hotspots
 * Returns hotspot data (protected — requires auth)
 */
router.get("/", protect, async (req, res) => {
  try {
    // Group reports by lat/lng (rounded) so nearby points merge.
    // Note: Mongo stores location.latitude/longitude.
    const pipeline = [
      {
        $match: {
          "location.latitude": { $ne: null },
          "location.longitude": { $ne: null },
        },
      },
      {
        $addFields: {
          lat_r: { $round: ["$location.latitude", 3] },
          lng_r: { $round: ["$location.longitude", 3] },
        },
      },
      {
        $sort: { timestamp: -1 },
      },
      {
        $group: {
          _id: { lat: "$lat_r", lng: "$lng_r" },
          reports: { $sum: 1 },
          latestUrl: { $first: "$url" },
          latestDomain: { $first: "$domain" },
        },
      },
      { $sort: { reports: -1 } },
      { $limit: 200 },
    ];

    const grouped = await Report.aggregate(pipeline);

    const data = grouped.map((g) => {
      const count = g.reports || 1;
      const domain = g.latestDomain || "Unknown";
      return {
        lat: g._id.lat,
        lng: g._id.lng,
        city: domain, // reuse existing UI field; shows domain in popup header
        risk: riskFromCount(count),
        reports: count,
        incident: g.latestUrl || "Reported phishing incident",
      };
    });

    res.json({ success: true, count: data.length, data });
  } catch (err) {
    console.error("hotspots error:", err);
    res.status(500).json({ success: false, message: "Failed to load hotspots" });
  }
});

module.exports = router;
