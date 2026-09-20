import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { NasaMetricCard } from "./NasaMetricCard";
import { getFleetSnapshot } from "./data";
import { getEngineDetails, getEngines } from "../../services/dashboardApi";

export function EngineDetailsPage() {
  const [engineId, setEngineId] = useState("");
  const [score, setScore] = useState<number | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const engines = await getEngines();
        if (engines.length === 0) {
          setEngineId("");
          setScore(null);
          return;
        }
        const selectedEngineId = engines[0].engine_id;
        setEngineId(selectedEngineId);
        const details = await getEngineDetails(selectedEngineId);
        if (details.length > 0) {
          setScore(details[details.length - 1].anomaly_score);
        } else {
          setScore(null);
        }
      } catch {
        setEngineId("");
        setScore(null);
      }
    };

    void load();
  }, []);

  const hasLiveData = Boolean(engineId) && score !== null;

  const engine = useMemo(() => {
    const anomalyScore = Number(score ?? 0);
    const failureRisk = Math.min(100, Math.max(0, anomalyScore * 100));
    const healthScore = Math.max(0, 100 - failureRisk);
    const rul = Math.max(0, Math.round((1 - anomalyScore) * 100));

    return {
      engineId: engineId || "No engine",
      healthScore,
      rul,
      failureRisk,
      anomalyScore,
    };
  }, [engineId, score]);

  const telemetryHistory = Array.from({ length: 24 }, (_, i) => ({
    t: `${i}:00`,
    temperature: 690 + (i % 6) * 7,
    vibration: 3.1 + (i % 5) * 0.2,
    anomaly: Math.min(1, score - 0.2 + (i % 7) * 0.03),
    prediction: 45 + i,
    rul: Math.max(20, engine.rul - i),
    risk: Math.min(99, engine.failureRisk + i),
  }));

  if (!hasLiveData) {
    return (
      <div className="p-6 bg-background min-h-full">
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <h1 className="text-2xl font-semibold text-foreground">Engine Details</h1>
          <p className="mt-2 text-muted-foreground">No live engine telemetry available yet. Start the simulator to populate this view.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-background min-h-full">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Engine Details</h1>
        <p className="text-muted-foreground mt-1">Deep-dive diagnostics and predictions for {engine.engineId}.</p>
      </div>

      <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle>Engine Overview Card</CardTitle>
          <CardDescription>Current predictive maintenance status</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <NasaMetricCard title="Health Score" value={`${engine.healthScore}%`} subtitle="Model weighted score" />
          <NasaMetricCard title="Current RUL" value={`${engine.rul} cycles`} subtitle="Estimated cycles remaining" />
          <NasaMetricCard title="Failure Risk" value={`${engine.failureRisk}%`} subtitle="Probabilistic risk estimate" />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Telemetry History</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line dataKey="temperature" stroke="#f97316" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Sensor Performance Chart</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line dataKey="vibration" stroke="#3b82f6" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Anomaly Timeline</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Line dataKey="anomaly" stroke="#ef4444" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Prediction History</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line dataKey="prediction" stroke="#6366f1" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>RUL Forecast</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line dataKey="rul" stroke="#14b8a6" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Failure Risk Trend</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line dataKey="risk" stroke="#dc2626" strokeWidth={2.2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Sensor Values</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Sensor</TableHead><TableHead>Value</TableHead></TableRow></TableHeader>
              <TableBody>
                <TableRow><TableCell>T24</TableCell><TableCell>643 C</TableCell></TableRow>
                <TableRow><TableCell>P30</TableCell><TableCell>44.8 psi</TableCell></TableRow>
                <TableRow><TableCell>Nf</TableCell><TableCell>7240 rpm</TableCell></TableRow>
                <TableRow><TableCell>Vibration</TableCell><TableCell>4.2 mm/s</TableCell></TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Prediction History</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Model</TableHead><TableHead>Output</TableHead></TableRow></TableHeader>
              <TableBody>
                <TableRow><TableCell>RUL-LSTM v4</TableCell><TableCell>51 cycles</TableCell></TableRow>
                <TableRow><TableCell>Risk-XGBoost v3</TableCell><TableCell>69%</TableCell></TableRow>
                <TableRow><TableCell>Anomaly-AE v2</TableCell><TableCell>0.81</TableCell></TableRow>
                <TableRow><TableCell>Status</TableCell><TableCell><Badge variant="outline">Warning</Badge></TableCell></TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border-border/30 shadow-sm bg-card/80 backdrop-blur-sm">
          <CardHeader><CardTitle>Alert History</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>ID</TableHead><TableHead>Severity</TableHead></TableRow></TableHeader>
              <TableBody>
                <TableRow><TableCell>AL-9007</TableCell><TableCell>High</TableCell></TableRow>
                <TableRow><TableCell>AL-8978</TableCell><TableCell>Medium</TableCell></TableRow>
                <TableRow><TableCell>AL-8951</TableCell><TableCell>Low</TableCell></TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
