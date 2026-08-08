import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  FastForward,
  Pause,
  Play,
  RefreshCcw,
  Siren,
  Wind,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Slider } from "../ui/slider";
import { Badge } from "../ui/badge";

type SegmentName = "Fan" | "Compressor" | "Combustor" | "Turbine" | "Exhaust";
type SegmentState = "healthy" | "degrading" | "critical";
type PlaybackStatus = "LIVE" | "PLAYING" | "PAUSED" | "FAULT DETECTED";

type TelemetryState = {
  rpm: number;
  temperature: number;
  pressure: number;
  fuelFlow: number;
  vibration: number;
  anomaly: number;
  risk: number;
  health: number;
  rul: number;
};

type SimPoint = {
  x: number;
  telemetry: number;
  rul: number;
  risk: number;
  anomaly: number;
  rpm: number;
  temp: number;
  pressure: number;
  fuel: number;
  vibration: number;
};

const BASE_TELEMETRY: TelemetryState = {
  rpm: 7410,
  temperature: 682,
  pressure: 44,
  fuelFlow: 85,
  vibration: 2.7,
  anomaly: 0.31,
  risk: 38,
  health: 86,
  rul: 118,
};

const COMPONENT_ORDER: SegmentName[] = ["Fan", "Compressor", "Combustor", "Turbine", "Exhaust"];

const INITIAL_COMPONENT_HEALTH: Record<SegmentName, number> = {
  Fan: 98,
  Compressor: 91,
  Combustor: 85,
  Turbine: 63,
  Exhaust: 94,
};

const FAULTS = ["Bearing Failure", "Fan Damage", "Fuel Leak", "Sensor Drift", "Overheating"];

const SPEED_FACTORS: Record<string, number> = {
  "1x": 1,
  "5x": 5,
  "10x": 10,
  "25x": 25,
  "50x": 50,
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function segmentState(health: number): SegmentState {
  if (health >= 82) return "healthy";
  if (health >= 60) return "degrading";
  return "critical";
}

function segmentClasses(state: SegmentState): string {
  if (state === "healthy") {
    return "from-green-500/40 via-green-500/20 to-green-700/60 border-green-400/60";
  }
  if (state === "degrading") {
    return "from-yellow-400/40 via-yellow-500/20 to-orange-500/60 border-yellow-300/70";
  }
  return "from-red-500/50 via-red-500/25 to-red-800/70 border-red-300/70";
}

function statusClass(status: PlaybackStatus): string {
  if (status === "LIVE") return "bg-emerald-500/15 text-emerald-700 border-emerald-500/40";
  if (status === "PLAYING") return "bg-sky-500/15 text-sky-700 border-sky-500/40";
  if (status === "PAUSED") return "bg-slate-500/15 text-slate-700 border-slate-500/40";
  return "bg-red-500/15 text-red-700 border-red-500/40";
}

function GaugeCard({
  label,
  value,
  min,
  max,
  unit,
  trend,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  trend: Array<{ x: number; y: number }>;
}) {
  const clamped = clamp(value, min, max);
  const pct = ((clamped - min) / (max - min)) * 100;
  const angle = -120 + (pct / 100) * 240;

  return (
    <Card className="border-border/40 bg-card/70 backdrop-blur-sm">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <p className="text-xs text-muted-foreground">{unit}</p>
        </div>

        <div className="relative h-20">
          <svg viewBox="0 0 180 90" className="w-full h-full">
            <path d="M 20 80 A 70 70 0 0 1 160 80" stroke="hsl(var(--muted))" strokeWidth="10" fill="none" />
            <path
              d="M 20 80 A 70 70 0 0 1 160 80"
              stroke="hsl(var(--primary))"
              strokeWidth="10"
              fill="none"
              strokeDasharray={`${(pct / 100) * 220} 220`}
              className="transition-all duration-500"
            />
            <g transform={`translate(90 80) rotate(${angle})`}>
              <line x1="0" y1="0" x2="0" y2="-56" stroke="hsl(var(--foreground))" strokeWidth="3" strokeLinecap="round" />
            </g>
            <circle cx="90" cy="80" r="5" fill="hsl(var(--foreground))" />
          </svg>
          <div className="absolute inset-x-0 bottom-0 text-center">
            <p className="text-lg font-semibold text-foreground">{value.toFixed(unit === "x" ? 2 : 0)}</p>
          </div>
        </div>

        <div className="h-14">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend}>
              <Area type="monotone" dataKey="y" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.15} strokeWidth={1.6} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function RadialGauge({ label, value, color }: { label: string; value: number; color: string }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamp(value, 0, 100) / 100) * circumference;

  return (
    <Card className="border-border/40 bg-card/70 backdrop-blur-sm">
      <CardContent className="p-4 flex items-center gap-4">
        <div className="relative h-24 w-24">
          <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
            <circle cx="60" cy="60" r={radius} stroke="hsl(var(--muted))" strokeWidth="12" fill="none" />
            <circle
              cx="60"
              cy="60"
              r={radius}
              stroke={color}
              strokeWidth="12"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="transition-all duration-700"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-semibold text-foreground">{Math.round(value)}%</span>
          </div>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-xs text-muted-foreground mt-1">AI-updated in real-time</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function SimulationLabPage() {
  const [dataset, setDataset] = useState("FD001");
  const [engine, setEngine] = useState("E-1024");
  const [speed, setSpeed] = useState("1x");
  const [running, setRunning] = useState(false);
  const [timeline, setTimeline] = useState(12);
  const [faults, setFaults] = useState<string[]>([]);

  const [telemetry, setTelemetry] = useState<TelemetryState>(BASE_TELEMETRY);

  const [series, setSeries] = useState<SimPoint[]>(
    Array.from({ length: 32 }, (_, i) => ({
      x: i,
      telemetry: 662 + (i % 6) * 8,
      rul: 140 - i,
      risk: 24 + i * 1.2,
      anomaly: 0.19 + i * 0.013,
      rpm: 7350 + (i % 7) * 20,
      temp: 668 + (i % 8) * 6,
      pressure: 41 + (i % 6),
      fuel: 80 + (i % 8),
      vibration: 2 + (i % 6) * 0.2,
    })),
  );

  const speedFactor = SPEED_FACTORS[speed];

  useEffect(() => {
    if (!running) return;

    const interval = setInterval(() => {
      setTimeline((prev) => (prev + 1) % 101);

      setTelemetry((prev) => {
        const faultIntensity = faults.length;
        const bearing = faults.includes("Bearing Failure") ? 1 : 0;
        const fanDamage = faults.includes("Fan Damage") ? 1 : 0;
        const fuelLeak = faults.includes("Fuel Leak") ? 1 : 0;
        const drift = faults.includes("Sensor Drift") ? 1 : 0;
        const overheating = faults.includes("Overheating") ? 1 : 0;

        const phase = Date.now() / (850 / speedFactor);

        const riskBoost = faultIntensity * 1.2 + bearing * 2.1 + overheating * 1.7;
        const anomalyBoost = faultIntensity * 0.018 + drift * 0.03;

        const nextTelemetry: TelemetryState = {
          rpm: clamp(prev.rpm + Math.sin(phase) * 26 - fanDamage * 14, 6800, 8600),
          temperature: clamp(prev.temperature + Math.cos(phase * 0.8) * 3 + overheating * 5, 620, 910),
          pressure: clamp(prev.pressure + Math.sin(phase * 1.2) * 0.8 - fuelLeak * 0.6, 30, 58),
          fuelFlow: clamp(prev.fuelFlow + Math.cos(phase * 0.6) * 1.2 + fuelLeak * 1.8, 62, 112),
          vibration: clamp(prev.vibration + Math.sin(phase * 0.9) * 0.08 + bearing * 0.2 + fanDamage * 0.12, 1.5, 7),
          anomaly: clamp(prev.anomaly + anomalyBoost - 0.004, 0.05, 0.99),
          risk: clamp(prev.risk + riskBoost - 0.4, 8, 99),
          health: clamp(prev.health - faultIntensity * 0.25 + 0.08, 18, 99),
          rul: clamp(prev.rul - (0.16 * speedFactor) / 4 - faultIntensity * 0.18, 0, 250),
        };

        setSeries((prevSeries) => {
          const nextX = prevSeries[prevSeries.length - 1].x + 1;
          const point: SimPoint = {
            x: nextX,
            telemetry: nextTelemetry.temperature,
            rul: nextTelemetry.rul,
            risk: nextTelemetry.risk,
            anomaly: nextTelemetry.anomaly,
            rpm: nextTelemetry.rpm,
            temp: nextTelemetry.temperature,
            pressure: nextTelemetry.pressure,
            fuel: nextTelemetry.fuelFlow,
            vibration: nextTelemetry.vibration,
          };
          return [...prevSeries.slice(-59), point];
        });

        return nextTelemetry;
      });
    }, Math.max(150, 1300 / speedFactor));

    return () => clearInterval(interval);
  }, [running, speedFactor, faults]);

  const playbackStatus: PlaybackStatus = useMemo(() => {
    if (faults.length > 0 || telemetry.risk >= 70) return "FAULT DETECTED";
    if (running) return "PLAYING";
    return timeline < 3 ? "LIVE" : "PAUSED";
  }, [faults.length, telemetry.risk, running, timeline]);

  const componentHealth = useMemo(() => {
    const values = { ...INITIAL_COMPONENT_HEALTH };

    if (faults.includes("Fan Damage")) values.Fan -= 34;
    if (faults.includes("Bearing Failure")) values.Turbine -= 22;
    if (faults.includes("Fuel Leak")) {
      values.Combustor -= 18;
      values.Exhaust -= 9;
    }
    if (faults.includes("Overheating")) {
      values.Combustor -= 22;
      values.Turbine -= 16;
    }
    if (faults.includes("Sensor Drift")) values.Compressor -= 12;

    const riskPenalty = Math.round((telemetry.risk - 30) / 7);
    COMPONENT_ORDER.forEach((name) => {
      values[name] = clamp(values[name] - riskPenalty, 12, 99);
    });

    return values;
  }, [faults, telemetry.risk]);

  const segmentStates = COMPONENT_ORDER.map((item) => segmentState(componentHealth[item]));

  const recommendation =
    faults.length > 0 || telemetry.risk > 65
      ? "Vibration trend increasing rapidly. Maintenance recommended within 15 cycles."
      : "Engine behavior within expected envelope. Continue simulation and monitor anomaly trajectory.";

  const replayMarkers = {
    anomaly: [14, 33, 46, 65, 77],
    warning: [29, 52, 72],
    critical: [83, 91],
    failure: [96],
  };

  const telemetryTrend = useMemo(
    () => ({
      rpm: series.slice(-16).map((p) => ({ x: p.x, y: p.rpm })),
      temp: series.slice(-16).map((p) => ({ x: p.x, y: p.temp })),
      pressure: series.slice(-16).map((p) => ({ x: p.x, y: p.pressure })),
      fuel: series.slice(-16).map((p) => ({ x: p.x, y: p.fuel })),
      vibration: series.slice(-16).map((p) => ({ x: p.x, y: p.vibration })),
    }),
    [series],
  );

  const toggleFault = (fault: string) => {
    setFaults((prev) =>
      prev.includes(fault) ? prev.filter((item) => item !== fault) : [...prev, fault],
    );
  };

  const resetSimulation = () => {
    setRunning(false);
    setTimeline(12);
    setFaults([]);
    setTelemetry(BASE_TELEMETRY);
  };

  const replay = () => {
    setTimeline(0);
    setRunning(true);
  };

  return (
    <div className="relative p-6 space-y-6 bg-background min-h-full overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="simlab-grid absolute inset-0 opacity-35" />
        <div className="simlab-radar absolute -top-24 -left-24 h-72 w-72 rounded-full" />
        <div className="simlab-radar absolute -bottom-24 right-8 h-72 w-72 rounded-full" />
      </div>

      <Card className="relative border-border/30 shadow-md bg-card/75 backdrop-blur-xl">
        <CardHeader className="pb-4">
          <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
            <div>
              <CardTitle className="text-2xl">Simulation Lab</CardTitle>
              <CardDescription>Aerospace Digital Twin Operations Center</CardDescription>
            </div>
            <Badge className={`border ${statusClass(playbackStatus)}`}>{playbackStatus}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-[1fr_1fr_auto_auto_auto_auto_170px] gap-3">
          <Select value={dataset} onValueChange={setDataset}>
            <SelectTrigger><SelectValue placeholder="Dataset" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="FD001">FD001</SelectItem>
              <SelectItem value="FD002">FD002</SelectItem>
              <SelectItem value="FD003">FD003</SelectItem>
              <SelectItem value="FD004">FD004</SelectItem>
            </SelectContent>
          </Select>

          <Select value={engine} onValueChange={setEngine}>
            <SelectTrigger><SelectValue placeholder="Engine" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="E-1024">E-1024</SelectItem>
              <SelectItem value="E-1028">E-1028</SelectItem>
              <SelectItem value="E-1039">E-1039</SelectItem>
              <SelectItem value="E-1042">E-1042</SelectItem>
            </SelectContent>
          </Select>

          <Button onClick={() => setRunning(true)} className="gap-2"><Play className="w-4 h-4" />Play</Button>
          <Button variant="outline" onClick={() => setRunning(false)} className="gap-2"><Pause className="w-4 h-4" />Pause</Button>
          <Button variant="outline" onClick={resetSimulation} className="gap-2"><RefreshCcw className="w-4 h-4" />Reset</Button>
          <Button variant="outline" onClick={replay} className="gap-2"><FastForward className="w-4 h-4" />Replay</Button>

          <Select value={speed} onValueChange={setSpeed}>
            <SelectTrigger><SelectValue placeholder="Speed" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="1x">1x</SelectItem>
              <SelectItem value="5x">5x</SelectItem>
              <SelectItem value="10x">10x</SelectItem>
              <SelectItem value="25x">25x</SelectItem>
              <SelectItem value="50x">50x</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <div className="relative grid grid-cols-1 2xl:grid-cols-[1.5fr_0.9fr] gap-6">
        <Card className="relative border-border/30 shadow-xl bg-card/80 overflow-hidden">
          <CardHeader>
            <CardTitle>Interactive Turbofan Digital Twin</CardTitle>
            <CardDescription>Fan | Compressor | Combustor | Turbine | Exhaust</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="relative rounded-2xl border border-border/40 bg-muted/30 p-6 min-h-[440px] overflow-hidden">
              <div className="absolute inset-0 pointer-events-none simlab-blueprint opacity-40" />

              <div className="absolute top-6 right-6 z-20 flex items-center gap-2 text-xs bg-background/70 border border-border/40 px-2 py-1 rounded-md">
                <Wind className="w-3 h-3 text-primary" /> Airflow Active
              </div>

              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[330px] w-[330px] rounded-full border border-primary/40 simlab-pulse-ring" />
              <div
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[410px] w-[410px] rounded-full pointer-events-none"
                style={{
                  background: `radial-gradient(circle, rgba(239,68,68,${Math.max(0, telemetry.risk / 280)}) 0%, rgba(239,68,68,0) 70%)`,
                }}
              />

              <div className="relative z-10 flex flex-col gap-4 pt-16">
                <div className="relative mx-auto w-full max-w-[920px] h-40 flex items-center justify-center">
                  <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

                  <div className="absolute left-8 top-1/2 -translate-y-1/2 h-24 w-24 rounded-full border border-border/60 bg-background/70 flex items-center justify-center overflow-hidden">
                    <div className="simlab-fan-rotor h-16 w-16 rounded-full border border-primary/50 relative">
                      <span className="absolute left-1/2 top-1/2 h-[2px] w-12 -translate-x-1/2 -translate-y-1/2 bg-primary/80" />
                      <span className="absolute left-1/2 top-1/2 h-12 w-[2px] -translate-x-1/2 -translate-y-1/2 bg-primary/80" />
                      <span className="absolute left-1/2 top-1/2 h-[2px] w-10 -translate-x-1/2 -translate-y-1/2 bg-primary/70 rotate-45" />
                      <span className="absolute left-1/2 top-1/2 h-[2px] w-10 -translate-x-1/2 -translate-y-1/2 bg-primary/70 -rotate-45" />
                    </div>
                  </div>

                  <div className="absolute inset-x-20 top-1/2 -translate-y-1/2 h-14 rounded-full border border-border/40 bg-background/30" />

                  <div className="relative z-10 grid grid-cols-5 gap-2 w-full max-w-[760px]">
                    {COMPONENT_ORDER.map((segment, idx) => {
                      const state = segmentStates[idx];
                      const isWarning = state !== "healthy";

                      return (
                        <div key={segment} className="space-y-2">
                          <div
                            className={`relative h-24 rounded-xl border bg-gradient-to-b ${segmentClasses(state)} shadow-inner overflow-hidden`}
                          >
                            <div className="absolute inset-0 opacity-60 simlab-scanline" />
                            {(segment === "Combustor" || segment === "Turbine") && state !== "healthy" && (
                              <div className="absolute inset-0 simlab-heat-glow" />
                            )}
                            {isWarning && (
                              <div className="absolute right-2 top-2">
                                <AlertTriangle className="w-4 h-4 text-yellow-100 simlab-blink" />
                              </div>
                            )}
                            <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-1">
                              <span className="text-xs text-white/90">{segment}</span>
                              <span className="text-base text-white font-semibold">{componentHealth[segment]}%</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {Array.from({ length: 10 }).map((_, i) => (
                    <span
                      key={i}
                      className="simlab-particle absolute block h-1.5 w-1.5 rounded-full bg-primary/60"
                      style={{
                        left: `${16 + i * 6.8}%`,
                        top: `${45 + (i % 4) * 2}%`,
                        animationDelay: `${(i % 8) * 0.28}s`,
                      }}
                    />
                  ))}
                </div>

                <div className="relative mt-3 rounded-lg border border-border/40 bg-background/55 p-3">
                  <div className="absolute left-3 right-3 top-1/2 border-t border-dashed border-primary/40" />
                  <div className="relative flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Predictive Failure Path</span>
                    <span className="text-red-500 font-medium">Projected threshold crossing at T+{Math.max(4, Math.round(telemetry.rul / 8))} cycles</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Card className="border-border/40 bg-card/75">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Health Score</p>
                <p className="text-2xl font-semibold text-foreground mt-1">{Math.round(telemetry.health)}%</p>
              </CardContent>
            </Card>
            <Card className="border-border/40 bg-card/75">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Failure Risk</p>
                <p className="text-2xl font-semibold text-red-500 mt-1">{Math.round(telemetry.risk)}%</p>
              </CardContent>
            </Card>
            <Card className="border-border/40 bg-card/75">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Remaining Useful Life</p>
                <p className="text-2xl font-semibold text-foreground mt-1">{Math.round(telemetry.rul)} cycles</p>
              </CardContent>
            </Card>
            <Card className="border-border/40 bg-card/75">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Current Anomaly Score</p>
                <p className="text-2xl font-semibold text-amber-500 mt-1">{telemetry.anomaly.toFixed(2)}</p>
              </CardContent>
            </Card>
          </div>

          <RadialGauge label="Failure Risk Gauge" value={telemetry.risk} color="#ef4444" />
          <RadialGauge label="Engine Health Gauge" value={telemetry.health} color="#22c55e" />

          <Card className="border-border/40 bg-card/75">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">AI Recommendation Panel</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-3 rounded-lg bg-muted/60 border border-border/40 text-sm">
                {recommendation}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Siren className="w-3.5 h-3.5 text-red-500" />
                Auto-alerting is {playbackStatus === "FAULT DETECTED" ? "escalated" : "monitoring"}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
        <GaugeCard label="RPM" value={telemetry.rpm} min={6500} max={9000} unit="rpm" trend={telemetryTrend.rpm} />
        <GaugeCard label="Temperature" value={telemetry.temperature} min={580} max={920} unit="C" trend={telemetryTrend.temp} />
        <GaugeCard label="Pressure" value={telemetry.pressure} min={30} max={60} unit="psi" trend={telemetryTrend.pressure} />
        <GaugeCard label="Fuel Flow" value={telemetry.fuelFlow} min={60} max={115} unit="kg/s" trend={telemetryTrend.fuel} />
        <GaugeCard label="Vibration" value={telemetry.vibration} min={1} max={8} unit="x" trend={telemetryTrend.vibration} />
      </div>

      <div className="grid grid-cols-1 2xl:grid-cols-[1.5fr_0.9fr] gap-6">
        <Card className="border-border/30 bg-card/80">
          <CardHeader>
            <CardTitle>Replay Timeline</CardTitle>
            <CardDescription>Scrub simulation history like a mission replay editor</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-xl border border-border/40 bg-muted/40 p-4">
              <div className="relative h-10 rounded-md bg-background/70 border border-border/40 overflow-hidden">
                <div className="absolute inset-y-0 left-0 bg-primary/30" style={{ width: `${timeline}%` }} />
                <div className="absolute inset-y-0 left-0 border-r-2 border-primary" style={{ left: `${timeline}%` }} />

                {replayMarkers.anomaly.map((mark) => (
                  <span key={`a-${mark}`} className="absolute top-0 h-full w-0.5 bg-sky-500/80" style={{ left: `${mark}%` }} title="Anomaly Detection" />
                ))}
                {replayMarkers.warning.map((mark) => (
                  <span key={`w-${mark}`} className="absolute top-0 h-full w-0.5 bg-yellow-500/80" style={{ left: `${mark}%` }} title="Warning Event" />
                ))}
                {replayMarkers.critical.map((mark) => (
                  <span key={`c-${mark}`} className="absolute top-0 h-full w-0.5 bg-red-500/90" style={{ left: `${mark}%` }} title="Critical Alert" />
                ))}
                {replayMarkers.failure.map((mark) => (
                  <span key={`f-${mark}`} className="absolute top-0 h-full w-1 bg-red-600" style={{ left: `${mark}%` }} title="Predicted Failure" />
                ))}
              </div>

              <div className="mt-4">
                <Slider value={[timeline]} min={0} max={100} step={1} onValueChange={(v) => setTimeline(v[0])} />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <Badge variant="outline" className="justify-center">Anomaly Detection</Badge>
              <Badge className="justify-center bg-yellow-500/10 text-yellow-700 border-yellow-500/30">Warning Events</Badge>
              <Badge className="justify-center bg-red-500/10 text-red-700 border-red-500/30">Critical Alerts</Badge>
              <Badge className="justify-center bg-red-700/15 text-red-700 border-red-700/30">Predicted Failure</Badge>
            </div>

            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="x" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line dataKey="risk" stroke="#ef4444" strokeWidth={2.5} dot={false} />
                  <Line dataKey="anomaly" stroke="#f59e0b" strokeWidth={2} dot={false} yAxisId={0} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-border/30 bg-card/80">
            <CardHeader>
              <CardTitle>Fault Injection Lab</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {FAULTS.map((fault) => (
                <Button
                  key={fault}
                  variant={faults.includes(fault) ? "default" : "outline"}
                  className="justify-start"
                  onClick={() => toggleFault(fault)}
                >
                  {fault}
                </Button>
              ))}
            </CardContent>
          </Card>

          <Card className="border-border/30 bg-card/80">
            <CardHeader>
              <CardTitle>Engine Component Health Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {COMPONENT_ORDER.map((component) => {
                const value = componentHealth[component];
                const color = value >= 82 ? "bg-green-500" : value >= 60 ? "bg-yellow-500" : "bg-red-500";

                return (
                  <div key={component}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span>{component}</span>
                      <span>{value}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div className={`h-full ${color} transition-all duration-500`} style={{ width: `${value}%` }} />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card className="border-border/30 bg-card/80">
            <CardHeader>
              <CardTitle>Sensor Status Map</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-5 gap-2">
              {Array.from({ length: 20 }).map((_, idx) => {
                const critical = telemetry.risk > 70 && idx % 6 === 0;
                const warn = telemetry.risk > 45 && idx % 4 === 0;
                const cls = critical ? "bg-red-500" : warn ? "bg-yellow-500" : "bg-green-500";

                return <div key={idx} className={`h-5 rounded-sm ${cls} transition-colors duration-300`} />;
              })}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
