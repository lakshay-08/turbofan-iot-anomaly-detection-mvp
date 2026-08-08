export interface ApiOverview {
  total_events: number;
  anomalies_detected: number;
  active_engines: number;
  models_running: number;
}

export interface ApiAnomaly {
  id: string;
  engine_id: string;
  timestamp: string | null;
  anomaly_score: number;
  is_anomaly: boolean;
  model_name: string;
  model_version?: string;
  metadata?: Record<string, unknown>;
}

export interface ApiAlert {
  id: string;
  engine_id: string;
  severity: string;
  message: string;
  created_at: string | null;
}

export interface ApiEngine {
  engine_id: string;
  last_seen: string;
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getOverview() {
  return request<ApiOverview>("/api/metrics/overview");
}

export function getRecentAnomalies(limit = 8) {
  return request<ApiAnomaly[]>(`/api/recent-anomalies?limit=${limit}`);
}

export function getAlerts() {
  return request<ApiAlert[]>("/api/alerts");
}

export function getEngines() {
  return request<ApiEngine[]>("/api/engines");
}

export function getEngineDetails(engineId: string) {
  return request<ApiAnomaly[]>(`/api/engine/${encodeURIComponent(engineId)}`);
}
