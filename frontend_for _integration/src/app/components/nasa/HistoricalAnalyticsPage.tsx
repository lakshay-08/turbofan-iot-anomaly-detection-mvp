import { useMemo, useState } from "react";
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
import { fleetHealthTrend, getFleetSnapshot } from "./data";

const severityOptions = ["all", "critical", "high", "medium", "low"];
const datasets = ["NASA CMAPSS FD001", "NASA CMAPSS FD002", "NASA CMAPSS FD003", "NASA CMAPSS FD004"];

const heatmapSensors = ["T24", "T30", "T50", "P30", "Nf", "Nc", "epr", "far", "W31", "W32"];

export function HistoricalAnalyticsPage() {
  const engines = getFleetSnapshot();
  const [engineId, setEngineId] = useState(engines[0].engineId);
  const [dataset, setDataset] = useState(datasets[0]);
  const [dateRange, setDateRange] = useState("last-30");
  const [severity, setSeverity] = useState("all");

  const timeline = useMemo(() => {
    const trend = fleetHealthTrend();
    return trend.map((item, i) => ({
      label: `W${i + 1}`,
      health: item.health - 1,
      rul: item.rul + 12,
      predictions: item.predictions + i * 14,
      anomalyCount: 6 + i * 2,
    }));
  }, []);

  const failureDistribution = [
    { bucket: "0-20", count: 5 },
    { bucket: "21-40", count: 11 },
    { bucket: "41-60", count: 17 },
    { bucket: "61-80", count: 13 },
    { bucket: "81-100", count: 6 },
  ];

  const comparison = engines.slice(0, 5).map((item) => ({
    engineId: item.engineId,
    health: item.healthScore,
    rul: item.rul,
  }));

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
              {timeline.slice(0, 6).map((point, idx) => (
                <TableRow key={point.label}>
                  <TableCell>{engines[idx % engines.length].engineId}</TableCell>
                  <TableCell>2026-07-{20 + idx} 11:2{idx}:00</TableCell>
                  <TableCell>{idx % 2 === 0 ? "HIGH" : "MEDIUM"}</TableCell>
                  <TableCell>{(0.41 + idx * 0.08).toFixed(2)}</TableCell>
                  <TableCell>{idx % 2 === 0 ? "Combustor instability" : "Sensor drift"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
