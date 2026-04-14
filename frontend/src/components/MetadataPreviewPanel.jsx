import { FiCheckSquare, FiChevronDown, FiEye, FiMap } from "react-icons/fi";

function buildMapUrl(lat, lon) {
  if (lat === null || lon === null || lat === undefined || lon === undefined) {
    return "";
  }
  const latNum = Number(lat);
  const lonNum = Number(lon);
  if (Number.isNaN(latNum) || Number.isNaN(lonNum)) {
    return "";
  }
  const bbox = `${lonNum - 0.03}%2C${latNum - 0.02}%2C${lonNum + 0.03}%2C${latNum + 0.02}`;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${latNum}%2C${lonNum}`;
}

function renderList(value) {
  if (!value) {
    return "-";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "-";
  }
  return value;
}

export default function MetadataPreviewPanel({ metadata, validationData, validationLoading, onValidate }) {
  const mapUrl = buildMapUrl(metadata.gps_latitude, metadata.gps_longitude);

  return (
    <section className="panel preview-panel">
      <div className="row between">
        <h2 className="title-with-icon"><FiEye /> Metadata Preview</h2>
        <span className="status-pill">Live Draft</span>
      </div>

      <div className="preview-grid">
        <div>
          <p className="preview-label">Title</p>
          <p>{renderList(metadata.title)}</p>
        </div>
        <div>
          <p className="preview-label">Date Taken</p>
          <p>{renderList(metadata.date_taken)}</p>
        </div>
        <div>
          <p className="preview-label">Description</p>
          <p>{renderList(metadata.description)}</p>
        </div>
        <div>
          <p className="preview-label">Keywords</p>
          <p>{renderList(metadata.keywords)}</p>
        </div>
        <div>
          <p className="preview-label">Creator</p>
          <p>{renderList(metadata.artist)}</p>
        </div>
        <div>
          <p className="preview-label">Location</p>
          <p>
            {metadata.city || ""} {metadata.state ? `, ${metadata.state}` : ""} {metadata.country ? `, ${metadata.country}` : ""}
          </p>
        </div>
      </div>
      {mapUrl ? (
        <div className="map-frame-wrap">
          <iframe title="metadata-map-preview" src={mapUrl} className="map-frame" loading="lazy" />
        </div>
      ) : (
        <p className="muted title-with-icon"><FiMap /> Add GPS coordinates to show map preview.</p>
      )}

      <details className="optional-validation" style={{ marginTop: "14px" }}>
        <summary className="title-with-icon">
          <FiChevronDown />
          Metadata Validation (Optional)
        </summary>
        <div style={{ marginTop: "10px" }}>
          <button className="btn-accent" type="button" onClick={onValidate} disabled={validationLoading}>
            <FiCheckSquare />
            {validationLoading ? "Opening and Validating..." : "Choose Folder and Validate"}
          </button>

          {validationData ? (
            <>
              <div className="kpi-grid" style={{ marginTop: "12px" }}>
                <article className="kpi-card">
                  <p className="kpi-label">Checked</p>
                  <p className="kpi-value">{validationData.checked_files}</p>
                </article>
                <article className="kpi-card">
                  <p className="kpi-label">Valid</p>
                  <p className="kpi-value">{validationData.valid_files}</p>
                </article>
                <article className="kpi-card">
                  <p className="kpi-label">Invalid</p>
                  <p className="kpi-value">{validationData.invalid_files}</p>
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
                    {validationData.results.slice(0, 100).map((item) => (
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
              Expand and run only when you need a consistency check.
            </p>
          )}
        </div>
      </details>
    </section>
  );
}
