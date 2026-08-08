import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { CommandCenterPage } from "./nasa/CommandCenterPage";
import { LiveMonitoringPage } from "./nasa/LiveMonitoringPage";
import { HistoricalAnalyticsPage } from "./nasa/HistoricalAnalyticsPage";
import { SimulationLabPage } from "./nasa/SimulationLabPage";
import { EngineDetailsPage } from "./nasa/EngineDetailsPage";
import { AlertsPage } from "./nasa/AlertsPage";

export function Layout() {
  const [currentPage, setCurrentPage] = useState("command-center");
  const [isDarkMode, setIsDarkMode] = useState(false);

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
      <main className="flex-1 overflow-auto">
        {renderContent()}
      </main>
    </div>
  );
}