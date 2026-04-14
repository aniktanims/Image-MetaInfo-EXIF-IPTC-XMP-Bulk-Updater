import { FiCpu, FiRadio } from "react-icons/fi";

function formatUptime(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hrs}h ${mins}m ${secs}s`;
}

function loadState(percent) {
  if (percent >= 90) {
    return "critical";
  }
  if (percent >= 70) {
    return "warn";
  }
  return "ok";
}

export default function SystemMetricsPanel({ metrics }) {
  if (!metrics) {
    return null;
  }

  const cpuState = loadState(metrics.cpu_percent);
  const memoryState = loadState(metrics.memory_percent);
  const diskState = loadState(metrics.disk_percent);
  const overallLoad = Math.max(metrics.cpu_percent, metrics.memory_percent, metrics.disk_percent);
  const overallState = loadState(overallLoad);
  const overallLabel = overallState === "critical" ? "Critical" : overallState === "warn" ? "Warning" : "Healthy";

  return (
    <section className="panel metrics-panel">
      <div className="row between">
        <h2 className="title-with-icon"><FiCpu /> Live System Metrics</h2>
        <div className="row">
          <span className={`status-pill system-health system-health-${overallState}`}>{overallLabel}</span>
          <span className="status-pill title-with-icon"><FiRadio /> Realtime</span>
        </div>
      </div>
      <div className="kpi-grid">
        <article className={`kpi-card load-card load-${cpuState}`}>
          <p className="kpi-label">CPU</p>
          <p className="kpi-value">{metrics.cpu_percent}%</p>
        </article>
        <article className={`kpi-card load-card load-${memoryState}`}>
          <p className="kpi-label">RAM</p>
          <p className="kpi-value">{metrics.memory_percent}%</p>
          <p className="muted">{metrics.memory_used_gb} / {metrics.memory_total_gb} GB</p>
        </article>
        <article className={`kpi-card load-card load-${diskState}`}>
          <p className="kpi-label">Disk Use</p>
          <p className="kpi-value">{metrics.disk_percent}%</p>
          <p className="muted">Free {metrics.disk_free_gb} GB</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">App Uptime</p>
          <p className="kpi-value" style={{ fontSize: "22px" }}>{formatUptime(metrics.uptime_seconds)}</p>
        </article>
      </div>
    </section>
  );
}
