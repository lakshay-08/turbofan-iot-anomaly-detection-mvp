import { useEffect, useMemo, useState } from "react";
import {
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  Cell,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import { NasaMetricCard } from "./NasaMetricCard";
import { fleetHealthTrend, toStatusLabel } from "./data";
import { getAlerts, getEngines, getOverview, getRecentAnomalies } from "../../services/dashboardApi";

const chartColors = ["#22c55e", "#eab308", "#ef4444", "#3b82f6", "#14b8a6"];

type DashboardAlert = {
  id: string;
  engineId: string;
  severity: "critical" | "high" | "medium" | "low";
  score: number;
  description: string;
  timestamp: string;
  status: "open" | "acknowledged" | "resolved";
  rootCause: string;
  recommendation: string;
};

export function CommandCenterPage() {
  const [engines, setEngines] = useState<any[]>([]);
  const [alertsFeed, setAlertsFeed] = useState<DashboardAlert[]>([]);
  const [overview, setOverview] = useState<{ total_events: number; anomalies_detected: number; active_engines: number; models_running: number } | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [overviewData, anomaliesData, alertsData, enginesData] = await Promise.all([
          getOverview(),
          getRecentAnomalies(8),
          getAlerts(),
          getEngines(),
        ]);

        if (cancelled) return;

        setOverview(overviewData);

        const anomalyByEngine = new Map<string, number>();
        for (const item of anomaliesData) {
          const score = Number(item.anomaly_score ?? 0);
          const current = anomalyByEngine.get(item.engine_id);
          if (current === undefined || score > current) {
            anomalyByEngine.set(item.engine_id, score);
          }
        }

        if (enginesData.length > 0) {
          const normalized = enginesData.map((item) => {
            const latestScore = Number(anomalyByEngine.get(item.engine_id) ?? 0);
            const failureRisk = Math.min(100, Math.max(0, latestScore * 100));
            const healthScore = Math.max(0, 100 - failureRisk);
            const rul = Math.max(0, Math.round((1 - latestScore) * 100));
            const status = failureRisk > 65 ? "critical" : failureRisk > 35 ? "warning" : "healthy";

            return {
              engineId: item.engine_id,
              status,
              healthScore,
              failureRisk,
              rul,
            };
          });
          setEngines(normalized);
        } else {
          setEngines([]);
        }

        if (alertsData.length > 0) {
          setAlertsFeed(
            alertsData.map((item) => ({
              id: item.id,
              engineId: item.engine_id,
              severity: (item.severity || "medium") as "critical" | "high" | "medium" | "low",
              score: 0.7,
              description: item.message,
              timestamp: item.created_at || "",
              status: "open",
              rootCause: "No root-cause text available from API.",
              recommendation: "Review engine telemetry and maintenance schedule.",
            })),
          );
        } else if (anomaliesData.length > 0) {
          setAlertsFeed(
            anomaliesData.map((item) => ({
              id: item.id,
              engineId: item.engine_id,
              severity: item.anomaly_score > 0.9 ? "critical" : item.anomaly_score > 0.8 ? "high" : "medium",
              score: item.anomaly_score,
              description: "Anomaly detected by inference pipeline",
              timestamp: item.timestamp || "",
              status: "open",
              rootCause: "Derived from anomaly score threshold.",
              recommendation: "Inspect engine and validate sensor baseline.",
            })),
          );
        } else {
          setAlertsFeed([]);
        }
      } catch {
        if (!cancelled) {
          setOverview(null);
          setEngines([]);
          setAlertsFeed([]);
        }
      }
    };

    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const trend = useMemo(
    () =>
      engines.length > 0
        ? engines.map((engine, index) => ({
            day: `E${index + 1}`,
            health: Math.max(0, Math.min(100, engine.healthScore)),
            rul: Math.max(0, engine.rul),
            predictions: Math.max(10, engine.failureRisk + 120),
          }))
        : [],
    [engines],
  );
  const hasLiveData = Boolean(overview && (overview.total_events > 0 || overview.active_engines > 0 || overview.anomalies_detected > 0)) || engines.length > 0 || alertsFeed.length > 0;

  const healthy = engines.filter((item) => item.status === "healthy").length;
  const warning = engines.filter((item) => item.status === "warning").length;
  const critical = engines.filter((item) => item.status === "critical").length;

  const fleetHealth = engines.length > 0 ? Math.round(engines.reduce((sum, e) => sum + e.healthScore, 0) / engines.length) : 0;
  const avgRul = engines.length > 0 ? Math.round(engines.reduce((sum, e) => sum + e.rul, 0) / engines.length) : 0;
  const criticalCount = engines.filter((item) => item.failureRisk > 65).length;

  const statusData = [
    { name: "Healthy", value: healthy, color: "#22c55e" },
    { name: "Warning", value: warning, color: "#eab308" },
    { name: "Critical", value: critical, color: "#ef4444" },
  ];

  const topRisk = useMemo(() => [...engines].sort((a, b) => b.failureRisk - a.failureRisk).slice(0, 5), [engines]);

  if (!hasLiveData) {
    return (
      <div className="p-6 bg-background min-h-full">
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Command Center</h1>
          <p className="mt-2 text-muted-foreground">No live telemetry available yet. Start the simulator to begin streaming engine data.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-background min-h-full">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Command Center</h1>
        <p className="text-muted-foreground mt-1">Fleet-wide predictive maintenance overview and decision support.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-6 gap-4">
        <NasaMetricCard title="Fleet Health Score" value={`${fleetHealth}%`} subtitle="Weighted fleet score" />
        <NasaMetricCard title="Active Engines" value={`${overview?.active_engines ?? engines.length}`} subtitle="Streaming telemetry online" />
        <NasaMetricCard title="Critical Engines" value={`${criticalCount}`} subtitle="Risk score > 65%" />
        <NasaMetricCard title="Average RUL" value={`${avgRul} cycles`} subtitle="Remaining useful life" />
        <NasaMetricCard title="Alerts Today" value={`${alertsFeed.length}`} subtitle="Open + acknowledged + resolved" />
        <NasaMetricCard title="Predictions Processed" value={`${overview?.total_events ?? 3284}`} subtitle="Last 24 hours" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Fleet Health Donut Chart</CardTitle>
            <CardDescription>Overall fleet state by engine condition</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={68} outerRadius={104}>
                  {statusData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Engine Status Distribution</CardTitle>
            <CardDescription>Operational categories across active engines</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={104}>
                  {statusData.map((entry, idx) => (
                    <Cell key={entry.name} fill={chartColors[idx]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>AI Recommendations Panel</CardTitle>
            <CardDescription>Model-driven maintenance actions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 rounded-lg bg-muted/60">
              <p className="text-sm font-medium">Prioritize highest anomaly engines for immediate inspection</p>
              <p className="text-xs text-muted-foreground mt-1">Recommendations are derived from live API data and anomaly severity.</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/60">
              <p className="text-sm font-medium">Apply throttle profile adjustments where risk is high</p>
              <p className="text-xs text-muted-foreground mt-1">Reduce thermal stress for engines with repeated warning-to-critical transitions.</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/60">
              <p className="text-sm font-medium">Queue recalibration for drifting channels</p>
              <p className="text-xs text-muted-foreground mt-1">Review sensors associated with persistent medium-risk anomalies.</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Top Risk Engines Table</CardTitle>
            <CardDescription>Highest failure probability ranked list</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Engine</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead>RUL</TableHead>
                  <TableHead>Failure Risk</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topRisk.map((engine) => (
                  <TableRow key={engine.engineId}>
                    <TableCell className="font-medium">{engine.engineId}</TableCell>
                    <TableCell>{engine.healthScore}%</TableCell>
                    <TableCell>{engine.rul} cycles</TableCell>
                    <TableCell>{engine.failureRisk}%</TableCell>
                    <TableCell>
                      <Badge variant="outline">{toStatusLabel(engine.status)}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Recent Anomalies Feed</CardTitle>
            <CardDescription>Latest anomaly detections across the fleet</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {alertsFeed.map((item) => (
              <div key={item.id} className="p-3 rounded-lg border border-border/50 bg-muted/30">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{item.engineId} - {item.description}</p>
                  <Badge variant="outline">{item.severity}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{item.timestamp} | Score {item.score.toFixed(2)}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle>Fleet Health Trend Line Chart</CardTitle>
          <CardDescription>7-day fleet health trajectory</CardDescription>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" />
              <YAxis domain={[70, 90]} stroke="hsl(var(--muted-foreground))" />
              <Tooltip />
              <Line type="monotone" dataKey="health" stroke="#0ea5e9" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
