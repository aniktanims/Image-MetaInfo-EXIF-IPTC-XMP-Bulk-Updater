import { useEffect, useMemo, useRef, useState } from "react";
import { FiMoon, FiSun } from "react-icons/fi";
import appLogo from "../tracktech-logo-nav-tall.avif";
import FolderPicker from "./components/FolderPicker";
import JobActivityPanel from "./components/JobActivityPanel";
import MetadataForm from "./components/MetadataForm";
import MetadataPreviewPanel from "./components/MetadataPreviewPanel";
import ProgressPanel from "./components/ProgressPanel";
import ResultsTable from "./components/ResultsTable";
import SystemMetricsPanel from "./components/SystemMetricsPanel";
import {
  cancelJob,
  createJob,
  getJob,
  getSystemMetrics,
  openJobSocket,
  scanFolder,
  selectFolder,
  validateFolder,
} from "./lib/api";

const initialMetadata = {
  date_taken: "",
  title: "TrackTECH Rubber Tracks",
  description:
    "TrackTECH Rubber Tracks | 4.714 Google reviews | Construction equipment supplier in Destin, Florida | Address: 216 Mountain Dr Ste 100, Destin, FL 32541 | Phone: (850) 816-7898",
  comment: "TrackTECH product and business imagery",
  headline: "TrackTECH Rubber Tracks - Destin, Florida",
  keywords: [
    "TrackTECH Rubber Tracks",
    "Construction equipment supplier",
    "Destin Florida",
    "Rubber Tracks",
  ],
  artist: "TrackTECH Rubber Tracks",
  credit: "TrackTECH Rubber Tracks",
  source: "TrackTECH Meta Updater",
  instructions: "Business media usage",
  copyright_text: "TrackTECH Rubber Tracks",
  software: "TrackTECH Meta Updater",
  rating: 5,
  location_name: "TrackTECH Rubber Tracks",
  city: "Destin",
  state: "Florida",
  country: "United States",
  country_code: "US",
  postal_code: "32541",
  contact_email: "",
  contact_url: "https://maps.app.goo.gl/9iAPapuyt8kh2aVKA",
  gps_latitude: 30.3954862,
  gps_longitude: -86.5060634,
  custom_fields: {
    business_name: "TrackTECH Rubber Tracks",
    google_reviews: "4.714",
    business_type: "Construction equipment supplier in Destin, Florida",
    address: "216 Mountain Dr Ste 100, Destin, FL 32541",
    phone: "(850) 816-7898",
    map_link: "https://maps.app.goo.gl/9iAPapuyt8kh2aVKA",
    google_maps_location:
      "https://www.google.com/maps/place/TrackTECH+Rubber+Tracks/@30.3954862,-86.5060634,17z/data=!4m6!3m5!1s0x8891415b579772b5:0x929235ee6852f254!8m2!3d30.3954862!4d-86.5060634!16s%2Fg%2F11msdslw_x?entry=ttu&g_ep=EgoyMDI2MDQwNy4wIKXMDSoASAFQAw%3D%3D",
  },
};

export default function App() {
  const [theme, setTheme] = useState("dark");
  const [folderPath, setFolderPath] = useState("");
  const [scanData, setScanData] = useState(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [folderPicking, setFolderPicking] = useState(false);
  const [outputFolderPicking, setOutputFolderPicking] = useState(false);
  const [error, setError] = useState("");
  const [validationData, setValidationData] = useState(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [systemMetrics, setSystemMetrics] = useState(null);

  const [metadata, setMetadata] = useState(initialMetadata);
  const [writeMode, setWriteMode] = useState("overwrite");
  const [outputFolder, setOutputFolder] = useState("");

  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [results, setResults] = useState([]);
  const [currentFile, setCurrentFile] = useState("");
  const [jobHistory, setJobHistory] = useState(() => {
    try {
      const raw = localStorage.getItem("metainfo_job_history_v1");
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const historyTrackedJobRef = useRef("");
  const socketRef = useRef(null);
  const [previewPage, setPreviewPage] = useState(1);

  const canStart = useMemo(() => {
    if (!scanData?.files?.length) {
      return false;
    }
    return true;
  }, [scanData]);

  const previewRows = scanData?.files ?? [];
  const previewPageSize = 50;
  const totalPreviewPages = Math.max(1, Math.ceil(previewRows.length / previewPageSize));
  const safePage = Math.min(previewPage, totalPreviewPages);
  const pagedPreviewRows = useMemo(() => {
    const start = (safePage - 1) * previewPageSize;
    return previewRows.slice(start, start + previewPageSize);
  }, [previewRows, safePage]);

  const completedCount = useMemo(
    () => results.filter((item) => item.status === "completed").length,
    [results]
  );
  const failedCount = useMemo(
    () => results.filter((item) => item.status === "failed").length,
    [results]
  );

  async function handleScan() {
    if (!folderPath) {
      return;
    }
    setError("");
    setScanLoading(true);
    try {
      const response = await scanFolder(folderPath);
      setScanData(response);
    } catch (scanError) {
      setError(scanError.message);
    } finally {
      setScanLoading(false);
    }
  }

  async function handlePickFolder() {
    setError("");
    setFolderPicking(true);
    try {
      const response = await selectFolder();
      setFolderPath(response.folder_path);
      setScanLoading(true);
      const scan = await scanFolder(response.folder_path);
      setScanData(scan);
    } catch (pickError) {
      setError(pickError.message);
    } finally {
      setScanLoading(false);
      setFolderPicking(false);
    }
  }

  async function handleValidateFolder() {
    setError("");
    setValidationLoading(true);
    try {
      const picked = await selectFolder();
      setFolderPath(picked.folder_path);
      const scan = await scanFolder(picked.folder_path);
      setScanData(scan);
      const result = await validateFolder(picked.folder_path);
      setValidationData(result);
    } catch (validationError) {
      setError(validationError.message);
    } finally {
      setValidationLoading(false);
    }
  }

  async function handleStartJob() {
    setError("");
    try {
      const payload = {
        files: scanData.all_files,
        metadata,
        write_mode: writeMode,
        output_folder: writeMode === "output_folder" ? outputFolder : null,
      };
      const response = await createJob(payload);
      setJobId(response.job_id);
      setResults([]);
      setCurrentFile("");
      historyTrackedJobRef.current = "";

      if (socketRef.current) {
        socketRef.current.close();
      }

      const refresh = async () => {
        const updated = await getJob(response.job_id);
        setJob(updated.summary);
        setResults(updated.results);
        if (["completed", "failed", "cancelled"].includes(updated.summary.status)) {
          socketRef.current?.close();
        }
      };

      await refresh();

      const socket = openJobSocket(response.job_id, async (eventPayload) => {
        try {
          if (eventPayload?.current_file) {
            setCurrentFile(eventPayload.current_file);
          }
          await refresh();
        } catch (refreshError) {
          setError(refreshError.message);
        }
      });
      socketRef.current = socket;

      socket.onclose = async () => {
        try {
          await refresh();
        } catch {
          // Ignore close-time refresh errors to avoid noisy UI while server restarts.
        }
      };
    } catch (jobError) {
      setError(jobError.message);
    }
  }

  async function handlePickOutputFolder() {
    setError("");
    setOutputFolderPicking(true);
    try {
      const response = await selectFolder();
      setOutputFolder(response.folder_path);
    } catch (pickError) {
      setError(pickError.message);
    } finally {
      setOutputFolderPicking(false);
    }
  }

  async function handleCancelJob() {
    try {
      await cancelJob(jobId);
    } catch (cancelError) {
      setError(cancelError.message);
    }
  }

  useEffect(() => {
    if (!jobId) {
      return;
    }
    const intervalId = setInterval(async () => {
      try {
        const updated = await getJob(jobId);
        setJob(updated.summary);
        setResults(updated.results);
      } catch {
        // Keep silent for transient network errors; websocket continues to drive updates.
      }
    }, 2000);

    return () => {
      clearInterval(intervalId);
    };
  }, [jobId]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const metrics = await getSystemMetrics();
        if (!cancelled) {
          setSystemMetrics(metrics);
        }
      } catch {
        // Ignore transient metrics errors.
      }
    };
    run();
    const intervalId = setInterval(run, 2000);
    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    setPreviewPage(1);
  }, [scanData?.folder_path]);

  useEffect(() => {
    if (!job || !jobId) {
      return;
    }
    if (!["completed", "failed", "cancelled"].includes(job.status)) {
      return;
    }
    if (historyTrackedJobRef.current === jobId) {
      return;
    }

    const newEntry = {
      job_id: jobId,
      status: job.status,
      processed_files: job.processed_files,
      total_files: job.total_files,
      failed_files: job.failed_files,
      finished_at: new Date().toISOString(),
    };

    setJobHistory((previous) => {
      const next = [newEntry, ...previous.filter((item) => item.job_id !== jobId)].slice(0, 15);
      localStorage.setItem("metainfo_job_history_v1", JSON.stringify(next));
      return next;
    });

    historyTrackedJobRef.current = jobId;
  }, [job, jobId]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const showJob = Boolean(job);
  const displayPath = (path) => {
    if (!path) {
      return "";
    }
    return path.replace(/^[A-Za-z]:\\/, "").replace(/\\/g, " > ");
  };

  return (
    <main className="app">
      <header className="hero">
        <div className="hero-top">
          <div className="brand-row">
            <img src={appLogo} alt="TrackTECH logo" className="app-logo" />
            <h1 className="brand-title">TrackTECH Meta Updater</h1>
          </div>
          <div className="row">
            <span className="status-pill">Production Dashboard</span>
            <button className="btn-secondary" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <FiSun /> : <FiMoon />} 
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
          </div>
        </div>
        <p>Bulk write or overwrite photo metadata for large folders, with live tracking designed for high-volume runs.</p>
      </header>

      <section className="kpi-grid">
        <article className="kpi-card">
          <p className="kpi-label">Scanned Files</p>
          <p className="kpi-value">{scanData?.total_files ?? 0}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Preview Loaded</p>
          <p className="kpi-value">{previewRows.length}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Completed</p>
          <p className="kpi-value">{completedCount}</p>
        </article>
        <article className="kpi-card">
          <p className="kpi-label">Failed</p>
          <p className="kpi-value">{failedCount}</p>
        </article>
      </section>

      <SystemMetricsPanel metrics={systemMetrics} />

      <FolderPicker
        folderPath={folderPath}
        onPickFolder={handlePickFolder}
        onFolderPathChange={(value) => setFolderPath(value)}
        onScan={handleScan}
        loading={scanLoading}
        pickingFolder={folderPicking}
      />

      {scanData ? (
        <section className="panel">
          <h2>Scan Summary</h2>
          <p>
            Found <strong>{scanData.total_files}</strong> supported photos. Showing first {scanData.files.length} in preview.
          </p>
          <p className="muted">
            Large-folder behavior: scanning runs in backend, and preview is capped and paginated in UI to stay smooth.
          </p>
        </section>
      ) : null}

      <section className="studio-layout">
        <div className="studio-main-col">
          <MetadataForm
            value={metadata}
            onChange={setMetadata}
            writeMode={writeMode}
            onWriteModeChange={setWriteMode}
            canStart={canStart}
            onStartProcessing={handleStartJob}
          />
        </div>
        <div className="studio-side-col">
          <div className="preview-logs-grid">
            <MetadataPreviewPanel
              metadata={metadata}
              validationData={validationData}
              validationLoading={validationLoading}
              onValidate={handleValidateFolder}
            />

            <JobActivityPanel
              job={job}
              results={results}
              currentFile={currentFile}
              jobHistory={jobHistory}
            />
          </div>

          {writeMode === "output_folder" ? (
            <section className="panel">
              <h2>Output Folder</h2>
              <div className="row">
                <button className="btn-secondary" onClick={handlePickOutputFolder} disabled={outputFolderPicking || scanLoading}>
                  {outputFolderPicking ? "Opening..." : "Choose Output Folder"}
                </button>
                <input
                  type="text"
                  placeholder="C:\\Users\\You\\Pictures\\UpdatedOutput"
                  value={outputFolder}
                  onChange={(event) => setOutputFolder(event.target.value)}
                />
              </div>
              <div className="folder-chip">{outputFolder ? displayPath(outputFolder) : "No output folder selected"}</div>
              {!outputFolder ? (
                <p className="muted">No folder selected: app will auto-create a new output folder when the job starts.</p>
              ) : null}
            </section>
          ) : null}

        </div>
      </section>

      {showJob ? <ProgressPanel summary={job} onCancel={handleCancelJob} /> : null}
      <ResultsTable results={results} />

      {previewRows.length ? (
        <section className="panel">
          <div className="row between">
            <h2>File Preview</h2>
            <div className="row pager-row">
              <button className="btn-secondary" disabled={safePage <= 1} onClick={() => setPreviewPage((page) => Math.max(1, page - 1))}>
                Prev
              </button>
              <span className="muted">
                Page {safePage} / {totalPreviewPages}
              </span>
              <button
                className="btn-secondary"
                disabled={safePage >= totalPreviewPages}
                onClick={() => setPreviewPage((page) => Math.min(totalPreviewPages, page + 1))}
              >
                Next
              </button>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Extension</th>
                  <th>Size (KB)</th>
                  <th>Path</th>
                </tr>
              </thead>
              <tbody>
                {pagedPreviewRows.map((item) => (
                  <tr key={item.path}>
                    <td>{item.name}</td>
                    <td>{item.extension}</td>
                    <td>{Math.round(item.size_bytes / 1024)}</td>
                    <td>{item.path}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      <footer className="footer-note">Developed by Mostofa Tanim Anik</footer>
    </main>
  );
}
