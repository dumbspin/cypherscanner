import React, { useMemo, useState } from "react";
import { login, register } from "../api/auth";
import "../../css/auth.css";

type Tab = "login" | "register";

const LoginPage: React.FC<{ onAuthed: () => void }> = ({ onAuthed }) => {
  const [tab, setTab] = useState<Tab>("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");

  const errId = tab === "login" ? "login-error" : "register-error";

  const clearError = () => setError(null);

  const onSubmitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!loginEmail.trim() || !loginPassword) {
      setError("Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const data = await login(loginEmail.trim(), loginPassword);
      if (!data.success) {
        setError(data.message || "Login failed");
        return;
      }
      localStorage.setItem("smartshield_token", data.token);
      localStorage.setItem("smartshield_user", JSON.stringify(data.user));
      onAuthed();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const onSubmitRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    if (!regName.trim() || !regEmail.trim() || !regPassword) {
      setError("Please fill in all fields");
      return;
    }
    if (regPassword.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    try {
      const data = await register(regName.trim(), regEmail.trim(), regPassword);
      if (!data.success) {
        setError(data.message || "Registration failed");
        return;
      }
      localStorage.setItem("smartshield_token", data.token);
      localStorage.setItem("smartshield_user", JSON.stringify(data.user));
      onAuthed();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="auth-bg">
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
        <div className="orb orb-3"></div>
        <div className="grid-overlay"></div>
      </div>

      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-brand">
            <div className="shield-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <h1>SmartShield</h1>
            <p>Phishing Hotspot Intelligence Platform</p>
          </div>

          <div className="auth-tabs">
            <button
              className={`auth-tab ${tab === "login" ? "active" : ""}`}
              onClick={() => {
                setTab("login");
                clearError();
              }}
              type="button"
            >
              Sign In
            </button>
            <button
              className={`auth-tab ${tab === "register" ? "active" : ""}`}
              onClick={() => {
                setTab("register");
                clearError();
              }}
              type="button"
            >
              Create Account
            </button>
          </div>

          {error && (
            <div className={`auth-error show`} id={errId}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span className="error-text">{error}</span>
            </div>
          )}

          {tab === "login" ? (
            <form className="auth-form active" onSubmit={onSubmitLogin}>
              <div className="form-group">
                <label>Email Address</label>
                <div className="input-wrapper">
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                  />
                  <span className="input-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="M22 7l-10 7L2 7" />
                    </svg>
                  </span>
                </div>
              </div>

              <div className="form-group">
                <label>Password</label>
                <div className="input-wrapper">
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                  />
                  <span className="input-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                </div>
              </div>

              <button type="submit" className={`btn-auth ${loading ? "loading" : ""}`} disabled={loading}>
                <span className="btn-text">Sign In to Dashboard</span>
                <span className="btn-loader"></span>
              </button>
            </form>
          ) : (
            <form className="auth-form active" onSubmit={onSubmitRegister}>
              <div className="form-group">
                <label>Full Name</label>
                <div className="input-wrapper">
                  <input
                    type="text"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    placeholder="John Doe"
                    required
                  />
                  <span className="input-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </span>
                </div>
              </div>

              <div className="form-group">
                <label>Email Address</label>
                <div className="input-wrapper">
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                  />
                  <span className="input-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="M22 7l-10 7L2 7" />
                    </svg>
                  </span>
                </div>
              </div>

              <div className="form-group">
                <label>Password</label>
                <div className="input-wrapper">
                  <input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Minimum 6 characters"
                    required
                    minLength={6}
                  />
                  <span className="input-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                </div>
              </div>

              <button type="submit" className={`btn-auth ${loading ? "loading" : ""}`} disabled={loading}>
                <span className="btn-text">Create Account</span>
                <span className="btn-loader"></span>
              </button>
            </form>
          )}

          <div className="auth-footer">🛡 Secured by SmartShield Intelligence</div>
        </div>
      </div>
    </>
  );
};

export default LoginPage;

