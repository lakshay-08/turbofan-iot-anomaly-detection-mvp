import { FormEvent, useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { CommandCenterPage } from "./nasa/CommandCenterPage";
import { LiveMonitoringPage } from "./nasa/LiveMonitoringPage";
import { HistoricalAnalyticsPage } from "./nasa/HistoricalAnalyticsPage";
import { SimulationLabPage } from "./nasa/SimulationLabPage";
import { EngineDetailsPage } from "./nasa/EngineDetailsPage";
import { AlertsPage } from "./nasa/AlertsPage";
import {
  AuthUser,
  clearAccessToken,
  getAccessToken,
  getCurrentUser,
  login,
} from "../services/dashboardApi";

export function Layout() {
  const [currentPage, setCurrentPage] = useState("command-center");
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [email, setEmail] = useState("admin@turbofan.local");
  const [password, setPassword] = useState("admin123!");

  useEffect(() => {
    const storedTheme = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const shouldUseDark = storedTheme ? storedTheme === "dark" : prefersDark;

    setIsDarkMode(shouldUseDark);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDarkMode);
    localStorage.setItem("theme", isDarkMode ? "dark" : "light");
  }, [isDarkMode]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }

    async function hydrateUser() {
      try {
        const user = await getCurrentUser();
        setCurrentUser(user);
      } catch {
        clearAccessToken();
        setCurrentUser(null);
      } finally {
        setAuthLoading(false);
      }
    }

    hydrateUser();
  }, []);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError("");

    try {
      const session = await login(email, password);
      setCurrentUser(session.user);
      setCurrentPage("command-center");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Unable to sign in.");
    }
  };

  const handleLogout = () => {
    clearAccessToken();
    setCurrentUser(null);
    setCurrentPage("command-center");
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(15,23,42,0.95),_rgba(2,6,23,1))] text-white">
        <div className="rounded-3xl border border-white/10 bg-white/5 px-8 py-6 shadow-2xl backdrop-blur-xl">
          <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Authenticating</p>
          <h1 className="mt-2 text-2xl font-semibold">Loading secure dashboard</h1>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(15,23,42,0.95),_rgba(2,6,23,1))] text-white">
        <div className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-10">
          <div className="grid w-full gap-8 rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-xl lg:grid-cols-[1.1fr_0.9fr] lg:p-10">
            <div className="space-y-6">
              <p className="text-sm uppercase tracking-[0.35em] text-cyan-300">Turbofan secure ops</p>
              <h1 className="max-w-xl text-4xl font-semibold leading-tight lg:text-6xl">
                Predictive maintenance dashboard with JWT authentication.
              </h1>
              <p className="max-w-2xl text-base text-slate-300 lg:text-lg">
                Sign in to inspect live telemetry, anomaly trends, and alert workflows backed by protected API routes.
              </p>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                  <div className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">Roles</div>
                  <div className="mt-2 text-sm text-slate-200">admin, operator, viewer</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                  <div className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">Auth</div>
                  <div className="mt-2 text-sm text-slate-200">Bearer token + local storage session</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                  <div className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">API</div>
                  <div className="mt-2 text-sm text-slate-200">Protected dashboard and prediction endpoints</div>
                </div>
              </div>
            </div>

            <form onSubmit={handleLogin} className="rounded-[1.75rem] border border-white/10 bg-slate-950/70 p-6 shadow-xl">
              <div className="mb-6">
                <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Login</p>
                <h2 className="mt-2 text-2xl font-semibold">Access the ops console</h2>
              </div>

              <label className="mb-4 block">
                <span className="mb-2 block text-sm text-slate-300">Email</span>
                <input
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition focus:border-cyan-300"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="email"
                />
              </label>

              <label className="mb-4 block">
                <span className="mb-2 block text-sm text-slate-300">Password</span>
                <input
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition focus:border-cyan-300"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
              </label>

              {authError ? <p className="mb-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{authError}</p> : null}

              <button
                type="submit"
                className="w-full rounded-2xl bg-cyan-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300"
              >
                Sign in
              </button>

              <p className="mt-4 text-sm text-slate-400">
                Use the bootstrap admin credentials configured in Docker Compose or your own admin account.
              </p>
            </form>
          </div>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    switch (currentPage) {
      case "command-center":
        return <CommandCenterPage />;
      case "live-monitoring":
        return <LiveMonitoringPage />;
      case "historical-analytics":
        return <HistoricalAnalyticsPage />;
      case "simulation-lab":
        return <SimulationLabPage />;
      case "engine-details":
        return <EngineDetailsPage />;
      case "alerts":
        return <AlertsPage />;
      default:
        return <CommandCenterPage />;
    }
  };

  return (
    <div className="flex h-screen bg-background">
      <div className="flex-shrink-0">
        <Sidebar
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          isDarkMode={isDarkMode}
          onToggleDarkMode={() => setIsDarkMode((prev) => !prev)}
        />
      </div>
      <main className="relative flex-1 overflow-auto">
        <div className="absolute right-6 top-6 z-20 flex items-center gap-3 rounded-full border border-white/10 bg-slate-950/80 px-4 py-2 text-sm text-white shadow-xl backdrop-blur">
          <span>{currentUser.email}</span>
          <span className="rounded-full bg-white/10 px-2 py-1 text-xs uppercase tracking-[0.2em] text-cyan-300">{currentUser.role}</span>
          <button onClick={handleLogout} className="text-slate-300 transition hover:text-white">
            Sign out
          </button>
        </div>
        {renderContent()}
      </main>
    </div>
  );
}