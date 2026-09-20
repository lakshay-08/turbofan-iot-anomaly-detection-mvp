import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { getAlerts, getEngines, getOverview, getRecentAnomalies } from "../../services/dashboardApi";

const severityOptions = ["all", "critical", "high", "medium", "low"];
const datasets = ["LIVE STREAM", "ALL ENGINES", "RECENT ANOMALIES"];

const heatmapSensors = ["T24", "T30", "T50", "P30", "Nf", "Nc", "epr", "far", "W31", "W32"];

function getSeverityLabel(score: number): string {
  if (score >= 0.8) return "critical";
  if (score >= 0.6) return "high";
  if (score >= 0.4) return "medium";
  return "low";
}

function matchesDateRange(timestamp: string | undefined, range: string): boolean {
  if (!timestamp) return true;

  try {
    const value = new Date(timestamp).getTime();
    const now = Date.now();
    const diffDays = (now - value) / (1000 * 60 * 60 * 24);

    if (range === "last-7") return diffDays <= 7;
    if (range === "last-30") return diffDays <= 30;
    if (range === "last-90") return diffDays <= 90;
    return true;
  } catch {
    return true;
  }
}

export function HistoricalAnalyticsPage() {
  const [engines, setEngines] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [overview, setOverview] = useState<any>(null);
  const [engineId, setEngineId] = useState("all");
  const [dataset, setDataset] = useState(datasets[0]);
  const [dateRange, setDateRange] = useState("last-30");
  const [severity, setSeverity] = useState("all");

  useEffect(() => {
    const load = async () => {
      try {
        const [overviewData, anomaliesData, enginesData, alertsData] = await Promise.all([
          getOverview(),
          getRecentAnomalies(200),
          getEngines(),
          getAlerts(),
        ]);

        setOverview(overviewData);
        setAnomalies(anomaliesData);

        const engineMap = new Map<string, number>();
        for (const item of anomaliesData) {
          const score = Number(item.anomaly_score ?? 0);
          const current = engineMap.get(item.engine_id);
          if (current === undefined || score > current) engineMap.set(item.engine_id, score);
        }

        const normalized = enginesData.map((item) => {
          const score = Number(engineMap.get(item.engine_id) ?? 0);
          const failureRisk = Math.min(100, Math.max(0, score * 100));
          const healthScore = Math.max(0, 100 - failureRisk);
          const rul = Math.max(0, Math.round((1 - score) * 120));
          return {
            engineId: item.engine_id,
            healthScore,
            rul,
            failureRisk,
            status: failureRisk > 65 ? "critical" : failureRisk > 35 ? "warning" : "healthy",
          };
        });

        setEngines(normalized);
        if (normalized.length > 0 && engineId === "all") setEngineId("all");
        if (alertsData.length > 0 && normalized.length === 0) setEngineId("all");
      } catch {
        setOverview(null);
        setAnomalies([]);
        setEngines([]);
      }
    };

    void load();
  }, []);

  const filteredAnomalies = useMemo(() => {
    const selectedSeverity = severity === "all" ? null : severity;

    return anomalies.filter((item) => {
      const score = Number(item.anomaly_score ?? 0);
      const itemSeverity = getSeverityLabel(score);
      const engineMatches = engineId === "all" || String(item.engine_id) === String(engineId);
      const severityMatches = !selectedSeverity || itemSeverity === selectedSeverity;
      const dateMatches = matchesDateRange(item.timestamp, dateRange);
      const datasetMatches =
        dataset === "LIVE STREAM"
          ? true
          : dataset === "RECENT ANOMALIES"
            ? score > 0.25
            : true;

      return engineMatches && severityMatches && dateMatches && datasetMatches;
    });
  }, [anomalies, dateRange, dataset, engineId, severity]);

  const timeline = useMemo(() => {
    const source = filteredAnomalies.length > 0 ? filteredAnomalies : [];
    return source.slice(0, 12).reverse().map((item, i) => ({
      label: `T${i + 1}`,
      health: Math.max(0, 100 - Number(item.anomaly_score ?? 0) * 100),
      rul: Math.max(0, Math.round((1 - Number(item.anomaly_score ?? 0)) * 120)),
      predictions: Math.max(1, Number(item.anomaly_score ?? 0) * 100 + 10),
      anomalyCount: Number(item.anomaly_score ?? 0) > 0.7 ? 10 : 4,
    }));
  }, [filteredAnomalies]);

  const failureDistribution = useMemo(() => {
    const buckets = ["0-20", "21-40", "41-60", "61-80", "81-100"];
    const counts = new Array(buckets.length).fill(0);

    filteredAnomalies.forEach((item) => {
      const score = Number(item.anomaly_score ?? 0) * 100;
      if (score <= 20) counts[0] += 1;
      else if (score <= 40) counts[1] += 1;
      else if (score <= 60) counts[2] += 1;
      else if (score <= 80) counts[3] += 1;
      else counts[4] += 1;
    });

    return buckets.map((bucket, index) => ({ bucket, count: counts[index] }));
  }, [filteredAnomalies]);

  const comparison = useMemo(
    () =>
      (engineId === "all" ? engines : engines.filter((item) => String(item.engineId) === String(engineId))).slice(0, 5).map((item) => ({
        engineId: item.engineId,
        health: item.healthScore,
        rul: item.rul,
      })),
    [engineId, engines],
  );

  return (
    <div className="p-6 space-y-6 bg-background min-h-full">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Historical Analytics</h1>
          <p className="text-muted-foreground mt-1">Analyze historical NASA engine data, trends, and model outputs.</p>
        </div>
        <Button>Export Analytics</Button>
      </div>

      <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <Select value={engineId} onValueChange={setEngineId}>
            <SelectTrigger><SelectValue placeholder="Engine ID" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Engines</SelectItem>
              {engines.map((engine) => (
                <SelectItem key={engine.engineId} value={engine.engineId}>{engine.engineId}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={dataset} onValueChange={setDataset}>
            <SelectTrigger><SelectValue placeholder="Dataset" /></SelectTrigger>
            <SelectContent>
              {datasets.map((item) => (
                <SelectItem key={item} value={item}>{item}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger><SelectValue placeholder="Date Range" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="last-7">Last 7 days</SelectItem>
              <SelectItem value="last-30">Last 30 days</SelectItem>
              <SelectItem value="last-90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>

          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger><SelectValue placeholder="Severity" /></SelectTrigger>
            <SelectContent>
              {severityOptions.map((item) => (
                <SelectItem key={item} value={item}>{item.toUpperCase()}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Engine Health Trend</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" />
                <YAxis domain={[60, 95]} />
                <Tooltip />
                <Line dataKey="health" stroke="#0ea5e9" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Remaining Useful Life Trend</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Line dataKey="rul" stroke="#14b8a6" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Failure Distribution Histogram</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={failureDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="bucket" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#f97316" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm xl:col-span-2">
          <CardHeader><CardTitle>Prediction Volume Timeline</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Line dataKey="predictions" stroke="#6366f1" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Anomaly Heatmap</CardTitle>
            <CardDescription>Weekly anomaly intensity per sensor channel</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {heatmapSensors.slice(0, 5).map((sensor, rowIdx) => (
                <div key={sensor} className="grid grid-cols-8 gap-2 items-center">
                  <div className="text-xs text-muted-foreground">{sensor}</div>
                  {Array.from({ length: 7 }, (_, colIdx) => {
                    const value = ((rowIdx + colIdx) * 13) % 100;
                    return (
                      <div
                        key={`${sensor}-${colIdx}`}
                        className="h-6 rounded"
                        style={{ backgroundColor: `rgba(239, 68, 68, ${0.12 + value / 120})` }}
                        title={`Intensity ${value}`}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Sensor Correlation Heatmap</CardTitle>
            <CardDescription>Correlation strengths across key features</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-2">
              {heatmapSensors.slice(0, 5).map((x) =>
                heatmapSensors.slice(5, 10).map((y, idx) => {
                  const value = ((x.charCodeAt(0) + y.charCodeAt(0) + idx) % 90) / 100;
                  return (
                    <div key={`${x}-${y}`} className="p-2 rounded text-center text-xs" style={{ backgroundColor: `rgba(14, 165, 233, ${0.15 + value})` }}>
                      {value.toFixed(2)}
                    </div>
                  );
                }),
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Engine Comparison Chart</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparison}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="engineId" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="health" fill="#22c55e" />
                <Bar dataKey="rul" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Root Cause Analysis Panel</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-sm font-medium">Primary Contributor: Thermal Fatigue</p>
              <p className="text-xs text-muted-foreground mt-1">Detected in turbine stages with rising EGT under repeated high-thrust cycles.</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-sm font-medium">Secondary Contributor: Sensor Drift</p>
              <p className="text-xs text-muted-foreground mt-1">Pressure channel offset increased by 3.6% over 90-cycle horizon.</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="text-sm font-medium">Suggested Action</p>
              <p className="text-xs text-muted-foreground mt-1">Schedule staged maintenance and retrain threshold model with latest run-to-failure traces.</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
        <CardHeader><CardTitle>Historical Anomaly Table</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Engine ID</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Anomaly Score</TableHead>
                <TableHead>Root Cause</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAnomalies.slice(0, 6).map((item, idx) => {
                const score = Number(item.anomaly_score ?? 0);
                const severityLabel = getSeverityLabel(score).toUpperCase();
                return (
                  <TableRow key={`${item.id ?? item.event_id ?? idx}`}>
                    <TableCell>{item.engine_id}</TableCell>
                    <TableCell>{item.timestamp ?? "—"}</TableCell>
                    <TableCell>{severityLabel}</TableCell>
                    <TableCell>{score.toFixed(2)}</TableCell>
                    <TableCell>{score > 0.7 ? "Combustor instability" : "Sensor drift"}</TableCell>
                  </TableRow>
                );
              })}
              {filteredAnomalies.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-6">
                    No historical records match the selected filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
