import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { NasaMetricCard } from "./NasaMetricCard";
import {
  getAlerts,
  getEngines,
  getOverview,
  getRecentAnomalies,
  getSimulatorStatus,
  type ApiAlert,
  type ApiAnomaly,
  type ApiEngine,
  type ApiOverview,
} from "../../services/dashboardApi";

export function LiveMonitoringPage() {
  const [simulatorRunning, setSimulatorRunning] = useState(false);
  const [overview, setOverview] = useState<ApiOverview | null>(null);
  const [alertsFeed, setAlertsFeed] = useState<ApiAlert[]>([]);
  const [engines, setEngines] = useState<ApiEngine[]>([]);
  const [anomalies, setAnomalies] = useState<ApiAnomaly[]>([]);

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        const [status, overviewData, alertsData, enginesData, anomaliesData] = await Promise.all([
          getSimulatorStatus(),
          getOverview(),
          getAlerts(),
          getEngines(),
          getRecentAnomalies(20),
        ]);

        if (cancelled) return;

        setSimulatorRunning(Boolean(status?.running));
        setOverview(overviewData);
        setAlertsFeed(alertsData);
        setEngines(enginesData);
        setAnomalies(anomaliesData);
      } catch {
        if (!cancelled) {
          setSimulatorRunning(false);
          setOverview(null);
          setAlertsFeed([]);
          setEngines([]);
          setAnomalies([]);
        }
      }
    };

    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const anomalyChart = useMemo(
    () =>
      [...anomalies]
        .reverse()
        .slice(0, 20)
        .map((item, index) => ({
          tick: `${index}`,
          anomaly: Number(item.anomaly_score ?? 0),
          timestamp: item.timestamp ?? "",
        })),
    [anomalies],
  );

  const latestAnomaly = anomalies[0]?.anomaly_score ?? 0;
  const latestAlert = alertsFeed[0];

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

  if (!overview && anomalies.length === 0 && alertsFeed.length === 0 && engines.length === 0) {
    return (
      <div className="p-6 bg-background min-h-full">
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Live Monitoring</h1>
          <p className="mt-2 text-muted-foreground">Simulation is active, but the backend has not produced telemetry yet. The stream should appear within a few seconds.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-background min-h-full">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Live Monitoring</h1>
          <p className="text-muted-foreground mt-1">Real-time telemetry generated from the active simulation pipeline.</p>
        </div>
        <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-500/20">Simulation active</Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <NasaMetricCard title="Active Engines" value={`${overview?.active_engines ?? engines.length}`} subtitle="Currently tracked" />
        <NasaMetricCard title="Total Events" value={`${overview?.total_events ?? 0}`} subtitle="Persisted predictions" />
        <NasaMetricCard title="Anomalies" value={`${overview?.anomalies_detected ?? anomalies.length}`} subtitle="Flagged events" />
        <NasaMetricCard title="Latest Score" value={`${latestAnomaly.toFixed(2)}`} subtitle="Most recent anomaly" />
        <NasaMetricCard title="Alerts" value={`${alertsFeed.length}`} subtitle="Open alert feed" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Real-Time Anomaly Score</CardTitle>
            <CardDescription>Latest anomaly signal from the live prediction pipeline</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={anomalyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="tick" hide />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <ReferenceLine y={0.7} stroke="#ef4444" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="anomaly" stroke="#ef4444" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Telemetry Volume</CardTitle>
            <CardDescription>Recent event count and anomaly trend</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={anomalyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="tick" hide />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Area type="monotone" dataKey="anomaly" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm xl:col-span-2">
          <CardHeader>
            <CardTitle>Engine Activity</CardTitle>
            <CardDescription>Tracked engines from the current backend dataset</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Engine ID</TableHead>
                  <TableHead>Last seen</TableHead>
                  <TableHead>Latest anomaly</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {engines.slice(0, 6).map((engine) => {
                  const latest = anomalies.find((item) => item.engine_id === engine.engine_id);
                  return (
                    <TableRow key={engine.engine_id}>
                      <TableCell className="font-medium">{engine.engine_id}</TableCell>
                      <TableCell>{engine.last_seen ? new Date(engine.last_seen).toLocaleTimeString() : "—"}</TableCell>
                      <TableCell>{latest ? latest.anomaly_score.toFixed(2) : "—"}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Latest Alert</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {latestAlert ? (
                <div className="p-3 rounded-lg bg-red-500/10 text-sm">
                  <div className="font-medium">{latestAlert.engine_id}</div>
                  <div className="text-muted-foreground mt-1">{latestAlert.message}</div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-muted/50 text-sm">No alerts generated yet.</div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Recent Events Feed</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {anomalies.slice(0, 5).map((item) => (
                <div key={item.id} className="p-2 rounded-lg bg-muted/50">
                  Engine {item.engine_id}: anomaly {Number(item.anomaly_score).toFixed(2)}
                </div>
              ))}
              {anomalies.length === 0 && <div className="p-2 rounded-lg bg-muted/50">Waiting for live inference data…</div>}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
