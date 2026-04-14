import { FiActivity, FiArchive, FiClock, FiFileText } from "react-icons/fi";

function fileNameFromPath(path) {
  if (!path) {
    return "-";
  }
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
}

function shortPath(path) {
  if (!path) {
    return "-";
  }
  return path.replace(/^[A-Za-z]:\\/, "").replace(/\\/g, " > ");
}

function statusBadgeClass(status) {
  if (status === "completed") {
    return "badge-completed";
  }
  if (status === "failed") {
    return "badge-failed";
  }
  return "badge-skipped";
}

function formatHistoryTime(isoValue) {
  if (!isoValue) {
    return "-";
  }
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
}

export default function JobActivityPanel({ job, results, currentFile, jobHistory }) {
  const latestLogs = (results || []).slice(-10).reverse();
  const percent = job?.total_files ? Math.round((job.processed_files / job.total_files) * 100) : 0;

  return (
    <section className="panel activity-panel">
      <div className="row between">
        <h2 className="title-with-icon"><FiActivity /> Processing Logs</h2>
        <span className="status-pill">Live Feed</span>
      </div>

      <article className="preview-side-card">
        <h3 className="title-with-icon"><FiActivity /> Live Image Progress</h3>
        {job ? (
          <>
            <p className="progress-modern-text" style={{ fontSize: "18px", marginTop: "6px" }}>
              {job.processed_files}/{job.total_files} done
            </p>
            <div className="progress-shell" style={{ height: "10px" }}>
              <div className="progress-fill" style={{ width: `${percent}%` }} />
            </div>
            <p className="muted title-with-icon"><FiClock /> Status: {job.status}</p>
            <p className="muted" style={{ marginTop: "6px" }}>
              Current image: <strong>{fileNameFromPath(currentFile)}</strong>
            </p>
            <p className="muted">{shortPath(currentFile)}</p>
          </>
        ) : (
          <p className="muted">Start a job to see live per-image progress here.</p>
        )}
      </article>

      <article className="preview-side-card">
        <h3 className="title-with-icon"><FiFileText /> Per-Image Log</h3>
        {latestLogs.length ? (
          <div className="preview-log-list">
            {latestLogs.map((item, index) => (
              <div className="preview-log-item" key={`${item.file_path}-${index}`}>
                <div className="row between">
                  <strong>{fileNameFromPath(item.file_path)}</strong>
                  <span className={`badge ${statusBadgeClass(item.status)}`}>{item.status}</span>
                </div>
                <p className="muted" style={{ margin: "4px 0 0" }}>{shortPath(item.file_path)}</p>
                {item.error ? <p className="error" style={{ margin: "4px 0 0" }}>{item.error}</p> : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No image log yet. Entries appear as each image is processed.</p>
        )}
      </article>

      <article className="preview-side-card">
        <h3 className="title-with-icon"><FiArchive /> Run History</h3>
        {jobHistory?.length ? (
          <div className="preview-history-list">
            {jobHistory.slice(0, 8).map((item) => (
              <div className="preview-history-item" key={item.job_id}>
                <div className="row between">
                  <span>#{item.job_id.slice(0, 8)}</span>
                  <span className={`badge ${statusBadgeClass(item.status)}`}>{item.status}</span>
                </div>
                <p className="muted" style={{ margin: "4px 0 0" }}>
                  {item.processed_files}/{item.total_files} processed, failed {item.failed_files}
                </p>
                <p className="muted" style={{ margin: "4px 0 0" }}>{formatHistoryTime(item.finished_at)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No history yet. Completed runs will be listed here.</p>
        )}
      </article>
    </section>
  );
}
