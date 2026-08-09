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

export interface AuthUser {
  id: string;
  email: string;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  created_at: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";
const AUTH_STORAGE_KEY = "turbofan.auth.token";

export function getAccessToken() {
  return localStorage.getItem(AUTH_STORAGE_KEY);
}

export function setAccessToken(token: string) {
  localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function clearAccessToken() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    if (response.status === 401) {
      clearAccessToken();
    }
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(`Login failed with status ${response.status}`);
  }

  const data = (await response.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function getCurrentUser() {
  return request<AuthUser>("/auth/me");
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
