export type Severity = "critical" | "high" | "medium" | "low";
export type EngineStatus = "healthy" | "warning" | "critical";

export interface EngineRecord {
  engineId: string;
  healthScore: number;
  rul: number;
  failureRisk: number;
  status: EngineStatus;
  anomalyScore: number;
  temperature: number;
  pressure: number;
  rpm: number;
  fuelFlow: number;
  vibration: number;
}

export interface AlertRecord {
  id: string;
  engineId: string;
  severity: Severity;
  score: number;
  description: string;
  timestamp: string;
  status: "open" | "acknowledged" | "resolved";
  rootCause: string;
  recommendation: string;
}

const baseEngines: EngineRecord[] = [
  { engineId: "E-1001", healthScore: 92, rul: 184, failureRisk: 14, status: "healthy", anomalyScore: 0.12, temperature: 642, pressure: 47, rpm: 7650, fuelFlow: 82, vibration: 2.4 },
  { engineId: "E-1007", healthScore: 87, rul: 151, failureRisk: 22, status: "healthy", anomalyScore: 0.21, temperature: 658, pressure: 46, rpm: 7520, fuelFlow: 84, vibration: 2.7 },
  { engineId: "E-1013", healthScore: 78, rul: 104, failureRisk: 37, status: "warning", anomalyScore: 0.44, temperature: 689, pressure: 45, rpm: 7390, fuelFlow: 88, vibration: 3.2 },
  { engineId: "E-1018", healthScore: 73, rul: 82, failureRisk: 49, status: "warning", anomalyScore: 0.58, temperature: 701, pressure: 44, rpm: 7310, fuelFlow: 91, vibration: 3.6 },
  { engineId: "E-1024", healthScore: 62, rul: 51, failureRisk: 69, status: "critical", anomalyScore: 0.81, temperature: 737, pressure: 42, rpm: 7190, fuelFlow: 96, vibration: 4.3 },
  { engineId: "E-1028", healthScore: 56, rul: 39, failureRisk: 77, status: "critical", anomalyScore: 0.88, temperature: 746, pressure: 41, rpm: 7140, fuelFlow: 98, vibration: 4.7 },
  { engineId: "E-1033", healthScore: 84, rul: 126, failureRisk: 29, status: "healthy", anomalyScore: 0.31, temperature: 671, pressure: 45, rpm: 7480, fuelFlow: 86, vibration: 2.9 },
  { engineId: "E-1039", healthScore: 68, rul: 67, failureRisk: 58, status: "warning", anomalyScore: 0.63, temperature: 714, pressure: 43, rpm: 7260, fuelFlow: 93, vibration: 3.9 },
];

export const alerts: AlertRecord[] = [
  {
    id: "AL-9012",
    engineId: "E-1028",
    severity: "critical",
    score: 0.93,
    description: "Bearing wear progression beyond threshold",
    timestamp: "2026-07-27 09:42:14",
    status: "open",
    rootCause: "High-pressure turbine bearing temperature drift with sustained vibration spikes.",
    recommendation: "Reduce thrust envelope and schedule immediate borescope + bearing inspection.",
  },
  {
    id: "AL-9007",
    engineId: "E-1024",
    severity: "high",
    score: 0.81,
    description: "Combustor instability signature detected",
    timestamp: "2026-07-27 08:17:02",
    status: "acknowledged",
    rootCause: "Fuel-air ratio oscillation detected under climb profile.",
    recommendation: "Run combustor tuning profile and verify injector balance.",
  },
  {
    id: "AL-8996",
    engineId: "E-1039",
    severity: "medium",
    score: 0.64,
    description: "Sensor drift in pressure channel",
    timestamp: "2026-07-27 07:09:35",
    status: "open",
    rootCause: "Static pressure transducer offset drift over 12 flight cycles.",
    recommendation: "Calibrate pressure sensor and compare against redundant channel.",
  },
  {
    id: "AL-8985",
    engineId: "E-1018",
    severity: "low",
    score: 0.33,
    description: "Minor fan imbalance trend",
    timestamp: "2026-07-27 06:42:11",
    status: "resolved",
    rootCause: "Low-amplitude imbalance from transient debris ingestion.",
    recommendation: "Monitor at next maintenance interval; no immediate action needed.",
  },
];

export function getFleetSnapshot(): EngineRecord[] {
  return baseEngines;
}

export function toStatusLabel(value: EngineStatus): string {
  if (value === "healthy") return "Healthy";
  if (value === "warning") return "Warning";
  return "Critical";
}

export function severityBadgeClass(value: Severity): string {
  if (value === "critical") return "bg-red-500/10 text-red-700 border-red-500/30";
  if (value === "high") return "bg-orange-500/10 text-orange-700 border-orange-500/30";
  if (value === "medium") return "bg-yellow-500/10 text-yellow-700 border-yellow-500/30";
  return "bg-blue-500/10 text-blue-700 border-blue-500/30";
}

export function fleetHealthTrend() {
  return [
    { day: "Mon", health: 84, rul: 118, predictions: 188 },
    { day: "Tue", health: 83, rul: 114, predictions: 204 },
    { day: "Wed", health: 82, rul: 110, predictions: 219 },
    { day: "Thu", health: 81, rul: 107, predictions: 231 },
    { day: "Fri", health: 80, rul: 103, predictions: 248 },
    { day: "Sat", health: 79, rul: 101, predictions: 236 },
    { day: "Sun", health: 81, rul: 105, predictions: 221 },
  ];
}

export function buildLiveTelemetry(seed: number) {
  const step = seed % 100;
  return {
    temperature: 660 + (step % 7) * 6,
    pressure: 45 + (step % 5),
    rpm: 7400 + (step % 10) * 22,
    fuelFlow: 85 + (step % 6) * 2,
    vibration: 2.5 + (step % 8) * 0.18,
    anomalyScore: Math.min(0.95, 0.2 + (step % 16) * 0.04),
  };
}
