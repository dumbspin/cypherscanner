// ============================================================
// SmartShield — JWT Auth Middleware
// ============================================================

const jwt = require("jsonwebtoken");
const User = require("../models/User");

const protect = async (req, res, next) => {
  let token;

  // Check for Bearer token in Authorization header
  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith("Bearer")
  ) {
    token = req.headers.authorization.split(" ")[1];
  }

  if (!token) {
    return res.status(401).json({
      success: false,
      message: "Not authorized — no token",
    });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = await User.findById(decoded.id);

    if (!req.user) {
      return res.status(401).json({
        success: false,
        message: "Not authorized — user not found",
      });
    }

    next();
  } catch (err) {
    return res.status(401).json({
      success: false,
      message: "Not authorized — invalid token",
    });
  }
};

/**
 * Page-level protection for server-rendered/static pages.
 * Accepts token from HttpOnly cookie (preferred) or Authorization header.
 */
const protectPage = async (req, res, next) => {
  let token = null;

  // Prefer cookie token for browser navigation
  if (req.cookies && req.cookies.smartshield_token) {
    token = req.cookies.smartshield_token;
  }

  // Fallback: Authorization header
  if (
    !token &&
    req.headers.authorization &&
    req.headers.authorization.startsWith("Bearer")
  ) {
    token = req.headers.authorization.split(" ")[1];
  }

  if (!token) {
    return res.redirect("/login");
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = await User.findById(decoded.id);
    if (!req.user) return res.redirect("/login");
    next();
  } catch (err) {
    return res.redirect("/login");
  }
};

module.exports = { protect, protectPage };
