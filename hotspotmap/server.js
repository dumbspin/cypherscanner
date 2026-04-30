// ============================================================
// SmartShield — Express Server
// ============================================================

require("dotenv").config();
const express = require("express");
const cors = require("cors");
const cookieParser = require("cookie-parser");
const path = require("path");
const connectDB = require("./config/db");
const { protectPage } = require("./middleware/auth");

// Connect to MongoDB
connectDB();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(cookieParser());

// Serve static files (css, js, etc.)
app.use(express.static(path.join(__dirname)));

// ---- API Routes ----
app.use("/api/auth", require("./routes/auth"));
app.use("/api/hotspots", require("./routes/hotspots"));

// ---- Page Routes ----

// Login page (default landing)
app.get("/login", (req, res) => {
  res.sendFile(path.join(__dirname, "login.html"));
});

// Dashboard (secure by default — server-side JWT check)
app.get("/dashboard", protectPage, (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// Back-compat alias
app.get("/dashboard-secure", (req, res) => res.redirect("/dashboard"));

// Root → redirect to login
app.get("/", (req, res) => {
  res.redirect("/login");
});

// ---- Start Server ----
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`
  ╔══════════════════════════════════════════╗
  ║   🛡  SmartShield Server Running         ║
  ║   🌐  http://localhost:${PORT}              ║
  ║   📡  MongoDB: ${process.env.MONGO_URI}     ║
  ╚══════════════════════════════════════════╝
  `);
});
