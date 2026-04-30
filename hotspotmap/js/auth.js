// ============================================================
// SmartShield — Auth Page JavaScript
// Handles login, register, tab switching, and token management
// ============================================================

(function () {
  // If already authenticated, redirect to dashboard
  const existingToken = localStorage.getItem("smartshield_token");
  if (existingToken) {
    window.location.href = "/dashboard";
    return;
  }

  // DOM Elements
  const tabBtns = document.querySelectorAll(".auth-tab");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const loginError = document.getElementById("login-error");
  const registerError = document.getElementById("register-error");

  // ---- Tab Switching ----
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;

      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".auth-form").forEach((f) => {
        f.classList.remove("active");
      });
      document.getElementById(`${target}-form`).classList.add("active");

      // Clear errors
      hideError(loginError);
      hideError(registerError);
    });
  });

  // ---- Error Helpers ----
  function showError(el, message) {
    el.querySelector(".error-text").textContent = message;
    el.classList.add("show");
  }

  function hideError(el) {
    el.classList.remove("show");
  }

  function setLoading(btn, loading) {
    if (loading) {
      btn.classList.add("loading");
      btn.disabled = true;
    } else {
      btn.classList.remove("loading");
      btn.disabled = false;
    }
  }

  // ---- Login Handler ----
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError(loginError);

    const btn = loginForm.querySelector(".btn-auth");
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    if (!email || !password) {
      showError(loginError, "Please fill in all fields");
      return;
    }

    setLoading(btn, true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!data.success) {
        showError(loginError, data.message || "Login failed");
        setLoading(btn, false);
        return;
      }

      // Store token and user info
      localStorage.setItem("smartshield_token", data.token);
      localStorage.setItem("smartshield_user", JSON.stringify(data.user));

      // Redirect to dashboard
      window.location.href = "/dashboard";
    } catch (err) {
      showError(loginError, "Network error. Please try again.");
      setLoading(btn, false);
    }
  });

  // ---- Register Handler ----
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError(registerError);

    const btn = registerForm.querySelector(".btn-auth");
    const name = document.getElementById("register-name").value.trim();
    const email = document.getElementById("register-email").value.trim();
    const password = document.getElementById("register-password").value;

    if (!name || !email || !password) {
      showError(registerError, "Please fill in all fields");
      return;
    }

    if (password.length < 6) {
      showError(registerError, "Password must be at least 6 characters");
      return;
    }

    setLoading(btn, true);

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      const data = await res.json();

      if (!data.success) {
        showError(registerError, data.message || "Registration failed");
        setLoading(btn, false);
        return;
      }

      // Store token and user info
      localStorage.setItem("smartshield_token", data.token);
      localStorage.setItem("smartshield_user", JSON.stringify(data.user));

      // Redirect to dashboard
      window.location.href = "/dashboard";
    } catch (err) {
      showError(registerError, "Network error. Please try again.");
      setLoading(btn, false);
    }
  });
})();
