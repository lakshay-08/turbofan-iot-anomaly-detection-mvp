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
import { buildLiveTelemetry, getFleetSnapshot, toStatusLabel } from "./data";

interface StreamPoint {
  tick: string;
  temperature: number;
  pressure: number;
  rpm: number;
  anomaly: number;
}

export function LiveMonitoringPage() {
  const fleet = getFleetSnapshot();
  const [seed, setSeed] = useState(1);
  const [stream, setStream] = useState<StreamPoint[]>(
    Array.from({ length: 20 }, (_, i) => {
      const telemetry = buildLiveTelemetry(i + 1);
      return {
        tick: `${i}`,
        temperature: telemetry.temperature,
        pressure: telemetry.pressure,
        rpm: telemetry.rpm,
        anomaly: telemetry.anomalyScore,
      };
    }),
  );

  useEffect(() => {
    const timer = setInterval(() => {
      setSeed((prevSeed) => {
        const nextSeed = prevSeed + 1;
        const point = buildLiveTelemetry(nextSeed);

        setStream((prev) => {
          const next = {
            tick: `${Date.now() % 10000}`,
            temperature: point.temperature,
            pressure: point.pressure,
            rpm: point.rpm,
            anomaly: point.anomalyScore,
          };

          return [...prev.slice(-39), next];
        });

        return nextSeed;
      });
    }, 2000);

    return () => clearInterval(timer);
  }, []);

  const latest = useMemo(() => buildLiveTelemetry(seed), [seed]);

  return (
    <div className="p-6 space-y-6 bg-background min-h-full">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Live Monitoring</h1>
          <p className="text-muted-foreground mt-1">Real-time engine telemetry with anomaly and threshold tracking.</p>
        </div>
        <Badge className="bg-primary/10 text-primary border-primary/20">Auto-updating every 2 seconds</Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <NasaMetricCard title="Temperature" value={`${latest.temperature} C`} subtitle="Turbine inlet" />
        <NasaMetricCard title="Pressure" value={`${latest.pressure} psi`} subtitle="Compressor outlet" />
        <NasaMetricCard title="RPM" value={`${latest.rpm}`} subtitle="Core shaft speed" />
        <NasaMetricCard title="Fuel Flow" value={`${latest.fuelFlow} kg/s`} subtitle="Live fuel demand" />
        <NasaMetricCard title="Vibration" value={`${latest.vibration.toFixed(2)} mm/s`} subtitle="Bearing vibration" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Real-Time Anomaly Score</CardTitle>
            <CardDescription>Streaming model confidence for abnormal behavior</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stream}>
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
            <CardTitle>Streaming Telemetry Chart</CardTitle>
            <CardDescription>Temperature and pressure trends over active stream</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stream}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="tick" hide />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="temperature" stroke="#f97316" fill="#f97316" fillOpacity={0.2} />
                <Area type="monotone" dataKey="pressure" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm xl:col-span-2">
          <CardHeader>
            <CardTitle>Threshold Monitoring</CardTitle>
            <CardDescription>RPM against guardrails</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stream}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="tick" hide />
                <YAxis domain={[7000, 7800]} />
                <Tooltip />
                <ReferenceLine y={7700} stroke="#ef4444" strokeDasharray="4 4" label="Critical" />
                <ReferenceLine y={7300} stroke="#eab308" strokeDasharray="4 4" label="Warning" />
                <Line type="monotone" dataKey="rpm" stroke="#14b8a6" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Top Risk Engines</CardTitle>
            <CardDescription>Live ranked by failure risk</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[...fleet]
              .sort((a, b) => b.failureRisk - a.failureRisk)
              .slice(0, 6)
              .map((engine) => (
                <div key={engine.engineId} className="p-2 rounded-lg bg-muted/50 flex items-center justify-between">
                  <span className="text-sm font-medium">{engine.engineId}</span>
                  <span className="text-sm text-muted-foreground">{engine.failureRisk}% risk</span>
                </div>
              ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm xl:col-span-2">
          <CardHeader>
            <CardTitle>Engine Health Status Table</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Engine ID</TableHead>
                  <TableHead>Health Score</TableHead>
                  <TableHead>Anomaly Score</TableHead>
                  <TableHead>RUL</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fleet.map((engine) => (
                  <TableRow key={engine.engineId}>
                    <TableCell className="font-medium">{engine.engineId}</TableCell>
                    <TableCell>{engine.healthScore}%</TableCell>
                    <TableCell>{engine.anomalyScore.toFixed(2)}</TableCell>
                    <TableCell>{engine.rul} cycles</TableCell>
                    <TableCell>
                      <Badge variant="outline">{toStatusLabel(engine.status)}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Active Alerts Feed</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="p-2 rounded-lg bg-red-500/10 text-sm">E-1028: Bearing failure probability spike</div>
              <div className="p-2 rounded-lg bg-orange-500/10 text-sm">E-1024: Combustor instability detected</div>
              <div className="p-2 rounded-lg bg-yellow-500/10 text-sm">E-1039: Sensor drift trend rising</div>
            </CardContent>
          </Card>

          <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
            <CardHeader>
              <CardTitle>Live Events Feed</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="p-2 rounded-lg bg-muted/50">Telemetry packet ingested for E-1001</div>
              <div className="p-2 rounded-lg bg-muted/50">Inference batch completed: 32 predictions</div>
              <div className="p-2 rounded-lg bg-muted/50">Auto-threshold rule updated for vibration channel</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
