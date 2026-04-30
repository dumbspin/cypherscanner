import React from "react";
import AuthGate from "./components/AuthGate";
import DashboardLayout from "./components/DashboardLayout";
import "../../css/styles.css";
import LoginPage from "./components/LoginPage";

const App: React.FC = () => {
  const [view, setView] = React.useState<"login" | "dashboard">("login");

  React.useEffect(() => {
    // On load, decide based on token.
    const token = localStorage.getItem("smartshield_token");
    setView(token ? "dashboard" : "login");
  }, []);

  return (
    <>
      {view === "login" ? (
        <LoginPage onAuthed={() => setView("dashboard")} />
      ) : (
        <AuthGate onUnauthed={() => setView("login")}>
          <DashboardLayout />
        </AuthGate>
      )}
    </>
  );
};

export default App;

