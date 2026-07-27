import { useEffect, useState } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE_URL || '';

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

function App() {
  const [overview, setOverview] = useState(null);
  const [recentAnomalies, setRecentAnomalies] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [engines, setEngines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [overviewData, anomaliesData, alertsData, enginesData] = await Promise.all([
          request('/api/metrics/overview'),
          request('/api/recent-anomalies?limit=8'),
          request('/api/alerts'),
          request('/api/engines'),
        ]);
        setOverview(overviewData);
        setRecentAnomalies(anomaliesData);
        setAlerts(alertsData);
        setEngines(enginesData);
      } catch (err) {
        setError(err.message || 'Unable to load dashboard metrics.');
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  return (
    <div className="dashboard-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Operations overview</p>
          <h1>Predictive maintenance monitoring</h1>
          <p className="hero-copy">
            Track anomaly scores, alert severity, and engine health from the streaming platform.
          </p>
        </div>
      </header>

      {loading ? (
        <p className="status">Loading dashboard…</p>
      ) : error ? (
        <p className="status status-error">{error}</p>
      ) : (
        <>
          <section className="stats-grid">
            <article className="stat-card">
              <span>Total events</span>
              <strong>{overview?.total_events ?? 0}</strong>
            </article>
            <article className="stat-card">
              <span>Anomalies detected</span>
              <strong>{overview?.anomalies_detected ?? 0}</strong>
            </article>
            <article className="stat-card">
              <span>Active engines</span>
              <strong>{overview?.active_engines ?? 0}</strong>
            </article>
            <article className="stat-card">
              <span>Models running</span>
              <strong>{overview?.models_running ?? 0}</strong>
            </article>
          </section>

          <section className="panels">
            <article className="panel">
              <div className="panel-header">
                <h2>Recent anomalies</h2>
              </div>
              {recentAnomalies.length === 0 ? (
                <p className="empty">No anomalies recorded yet.</p>
              ) : (
                <ul className="list">
                  {recentAnomalies.map((item) => (
                    <li key={item.id}>
                      <span>{item.engine_id}</span>
                      <span>{item.anomaly_score?.toFixed(3)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </article>

            <article className="panel">
              <div className="panel-header">
                <h2>Latest alerts</h2>
              </div>
              {alerts.length === 0 ? (
                <p className="empty">No alerts raised yet.</p>
              ) : (
                <ul className="list">
                  {alerts.map((alert) => (
                    <li key={alert.id}>
                      <span>{alert.engine_id}</span>
                      <span className={`pill ${alert.severity}`}>{alert.severity}</span>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          </section>

          <section className="panel">
            <div className="panel-header">
              <h2>Engine activity</h2>
            </div>
            {engines.length === 0 ? (
              <p className="empty">No engine activity available yet.</p>
            ) : (
              <table className="engine-table">
                <thead>
                  <tr>
                    <th>Engine</th>
                    <th>Last seen</th>
                  </tr>
                </thead>
                <tbody>
                  {engines.map((engine) => (
                    <tr key={engine.engine_id}>
                      <td>{engine.engine_id}</td>
                      <td>{new Date(engine.last_seen).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default App;
