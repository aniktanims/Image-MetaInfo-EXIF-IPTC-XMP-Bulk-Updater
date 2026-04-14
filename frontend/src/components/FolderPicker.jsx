import { FiFolder, FiFolderPlus, FiSearch } from "react-icons/fi";

export default function FolderPicker({
  folderPath,
  onPickFolder,
  onFolderPathChange,
  onScan,
  loading,
  pickingFolder,
}) {
  return (
    <section className="panel">
      <h2 className="title-with-icon"><FiFolder /> Select Photo Folder</h2>
      <p className="muted">Choose a folder with a native picker, then scan it.</p>
      <div className="row">
        <button className="btn-primary" onClick={onPickFolder} disabled={pickingFolder || loading}>
          <FiFolderPlus />
          {pickingFolder ? "Opening..." : "Choose Folder"}
        </button>
        <button className="btn-secondary" onClick={onScan} disabled={loading || !folderPath}>
          <FiSearch />
          {loading ? "Scanning..." : "Scan Folder"}
        </button>
      </div>
      <div className="row" style={{ marginTop: "10px" }}>
        <input
          type="text"
          placeholder="Paste folder path (example: /Users/you/Pictures)"
          value={folderPath}
          onChange={(event) => onFolderPathChange(event.target.value)}
        />
      </div>
      <div className="folder-chip">{folderPath || "No folder selected"}</div>
    </section>
  );
}
