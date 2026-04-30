// ============================================================
// SmartShield — Report Model (reads bot reports collection)
// ============================================================

const mongoose = require("mongoose");

const reportSchema = new mongoose.Schema(
  {
    url: { type: String, required: true },
    domain: { type: String, default: "" },
    description: { type: String, default: null },
    user_id: { type: String, required: true },
    timestamp: { type: Date, default: Date.now },
    location: {
      latitude: { type: Number, default: null },
      longitude: { type: Number, default: null },
    },
  },
  {
    // Important: your Python service already writes timestamps; we don't need Mongoose timestamps.
    timestamps: false,
    collection: "reports",
  }
);

module.exports = mongoose.model("Report", reportSchema);

