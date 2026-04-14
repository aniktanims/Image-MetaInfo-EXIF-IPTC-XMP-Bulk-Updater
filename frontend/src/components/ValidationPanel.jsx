export default function ValidationPanel({ data, loading, onRun }) {
  return (
    <section className="panel">
      <div className="row between">
        <h2>Metadata Validation</h2>
        <button className="btn-accent" onClick={onRun} disabled={loading}>
          {loading ? "Opening and Validating..." : "Choose Folder and Validate"}
        </button>
      </div>

      {data ? (
        <>
          <div className="kpi-grid" style={{ marginTop: "12px" }}>
            <article className="kpi-card">
              <p className="kpi-label">Checked</p>
              <p className="kpi-value">{data.checked_files}</p>
            </article>
            <article className="kpi-card">
              <p className="kpi-label">Valid</p>
              <p className="kpi-value">{data.valid_files}</p>
            </article>
            <article className="kpi-card">
              <p className="kpi-label">Invalid</p>
              <p className="kpi-value">{data.invalid_files}</p>
            </article>
          </div>

          <div className="table-wrap" style={{ marginTop: "12px" }}>
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Status</th>
                  <th>Issues</th>
                </tr>
              </thead>
              <tbody>
                {data.results.slice(0, 100).map((item) => (
                  <tr key={item.file_path}>
                    <td>{item.file_path}</td>
                    <td>
                      <span className={`badge ${item.valid ? "badge-completed" : "badge-failed"}`}>
                        {item.valid ? "valid" : "invalid"}
                      </span>
                    </td>
                    <td>{item.issues?.length ? item.issues.join(" | ") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="muted" style={{ marginTop: "8px" }}>
          Run a validation scan to verify metadata consistency before or after processing.
        </p>
      )}
    </section>
  );
}
