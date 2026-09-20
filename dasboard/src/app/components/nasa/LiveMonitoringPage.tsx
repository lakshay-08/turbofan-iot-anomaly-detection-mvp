import { useEffect, useState } from "react";
import { getSimulatorStatus } from "../../services/dashboardApi";

export function LiveMonitoringPage() {
  const [simulatorRunning, setSimulatorRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        const status = await getSimulatorStatus();
        if (!cancelled) {
          setSimulatorRunning(Boolean(status?.running));
        }
      } catch {
        if (!cancelled) {
          setSimulatorRunning(false);
        }
      }
    };

    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  if (!simulatorRunning) {
    return (
      <div className="p-6 bg-background min-h-full">
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Live Monitoring</h1>
          <p className="mt-2 text-muted-foreground">No live simulation is running. Start the Simulation Lab to activate this view.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-background min-h-full">
      <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
        <h1 className="text-2xl font-semibold text-foreground">Live Monitoring</h1>
        <p className="mt-2 text-muted-foreground">Simulation is active. The live telemetry stream will appear here once the backend is producing data.</p>
      </div>
    </div>
  );
}
