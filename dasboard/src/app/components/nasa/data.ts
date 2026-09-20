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

export const alerts: AlertRecord[] = [];

export function getFleetSnapshot(): EngineRecord[] {
  return [];
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
  return [];
}

export function buildLiveTelemetry(_: number) {
  return {
    temperature: 0,
    pressure: 0,
    rpm: 0,
    fuelFlow: 0,
    vibration: 0,
    anomalyScore: 0,
  };
}
