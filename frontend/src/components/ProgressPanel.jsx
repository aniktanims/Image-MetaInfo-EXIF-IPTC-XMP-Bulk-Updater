import { FiActivity, FiClock, FiXCircle } from "react-icons/fi";

export default function ProgressPanel({ summary, onCancel }) {
  const percent = summary.total_files
    ? Math.round((summary.processed_files / summary.total_files) * 100)
    : 0;

  const startedAt = summary.started_at ? new Date(summary.started_at) : null;
  const elapsedSeconds = startedAt ? Math.max(1, Math.floor((Date.now() - startedAt.getTime()) / 1000)) : 0;
  const rate = summary.processed_files > 0 ? summary.processed_files / elapsedSeconds : 0;
  const remaining = Math.max(0, summary.total_files - summary.processed_files);
  const etaSeconds = rate > 0 ? Math.round(remaining / rate) : 0;

  const formatEta = (seconds) => {
    if (!seconds || seconds < 1) {
      return "estimating...";
    }
    if (seconds < 60) {
      return `${seconds}s left`;
    }
    const mins = Math.round(seconds / 60);
    if (mins < 60) {
      return `${mins} min${mins > 1 ? "s" : ""} left`;
    }
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hrs}h ${remMins}m left`;
  };

  return (
    <section className="panel">
      <div className="row between">
        <h2 className="title-with-icon"><FiActivity /> Live Progress</h2>
        {summary.status === "running" ? (
          <button className="btn-danger" onClick={onCancel}>
            <FiXCircle /> Cancel Job
          </button>
        ) : null}
      </div>
      <div className="progress-shell">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
      <p className="progress-modern-text">
        {summary.processed_files}/{summary.total_files} - {formatEta(etaSeconds)}
      </p>
      <p className="muted">Status: {summary.status}</p>
      <p className="muted">Failed: {summary.failed_files}</p>
      <div className="row" style={{ marginTop: "8px" }}>
        <span className="status-pill">Speed: {rate.toFixed(2)} files/sec</span>
        <span className="status-pill title-with-icon"><FiClock /> ETA: {formatEta(etaSeconds)}</span>
      </div>
    </section>
  );
}
