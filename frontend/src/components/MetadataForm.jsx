import { useState } from "react";
import { FiEdit3, FiMapPin, FiPlayCircle } from "react-icons/fi";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

function splitKeywords(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

function extractCoordinatesFromMapLink(link) {
  const atMatch = link.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
  if (atMatch) {
    return { latitude: Number(atMatch[1]), longitude: Number(atMatch[2]) };
  }
  const dMatch = link.match(/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/);
  if (dMatch) {
    return { latitude: Number(dMatch[1]), longitude: Number(dMatch[2]) };
  }
  return null;
}

function exifToLocal(exifValue) {
  if (!exifValue) {
    return "";
  }
  const match = exifValue.match(/^(\d{4}):(\d{2}):(\d{2})\s(\d{2}):(\d{2}):(\d{2})$/);
  if (!match) {
    return "";
  }
  const [, year, month, day, hour, minute] = match;
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function exifToDate(exifValue) {
  const localValue = exifToLocal(exifValue);
  if (!localValue) {
    return null;
  }
  const date = new Date(localValue);
  return Number.isNaN(date.getTime()) ? null : date;
}

function localToExif(localValue) {
  if (!localValue) {
    return "";
  }
  const [datePart, timePart] = localValue.split("T");
  if (!datePart || !timePart) {
    return "";
  }
  const [year, month, day] = datePart.split("-");
  const [hour, minute] = timePart.split(":");
  return `${year}:${month}:${day} ${hour}:${minute}:00`;
}

function dateToExif(dateValue) {
  if (!dateValue) {
    return "";
  }
  const pad = (n) => String(n).padStart(2, "0");
  return `${dateValue.getFullYear()}:${pad(dateValue.getMonth() + 1)}:${pad(dateValue.getDate())} ${pad(
    dateValue.getHours()
  )}:${pad(dateValue.getMinutes())}:00`;
}

function csvToCustomFields(value) {
  const rows = value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const output = {};
  for (const row of rows) {
    const idx = row.indexOf("=");
    if (idx <= 0) {
      continue;
    }
    const key = row.slice(0, idx).trim();
    const val = row.slice(idx + 1).trim();
    if (key) {
      output[key] = val;
    }
  }
  return output;
}

function customFieldsToCsv(obj) {
  return Object.entries(obj || {})
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
}

export default function MetadataForm({
  value,
  onChange,
  writeMode,
  onWriteModeChange,
  renamePrefix,
  onRenamePrefixChange,
  renameStartIndex,
  onRenameStartIndexChange,
  renameNumberPosition,
  onRenameNumberPositionChange,
  canStart,
  onStartProcessing,
}) {
  const [mapLink, setMapLink] = useState("");
  const [customFieldText, setCustomFieldText] = useState(customFieldsToCsv(value.custom_fields));
  const [activeTab, setActiveTab] = useState("core");
  const previewStart = Number.isFinite(Number(renameStartIndex)) ? Math.max(1, Number(renameStartIndex)) : 1;
  const previewPrefix = (renamePrefix || "TrackTech x 450 x 450").trim() || "TrackTech x 450 x 450";
  const position = renameNumberPosition === "prefix" ? "prefix" : "suffix";
  const previewLine = (n) => (position === "prefix" ? `${n} - ${previewPrefix}` : `${previewPrefix} - ${n}`);

  const update = (field) => (event) => {
    onChange({ ...value, [field]: event.target.value });
  };

  const updateNumber = (field) => (event) => {
    const text = event.target.value.trim();
    onChange({ ...value, [field]: text === "" ? null : Number(text) });
  };

  const applyMapCoordinates = () => {
    const coords = extractCoordinatesFromMapLink(mapLink.trim());
    if (!coords) {
      return;
    }
    onChange({
      ...value,
      gps_latitude: coords.latitude,
      gps_longitude: coords.longitude,
    });
  };

  return (
    <section className="panel metadata-panel">
      <div className="metadata-head">
        <h2 className="title-with-icon"><FiEdit3 /> Metadata Studio</h2>
        <p className="muted">Apply rich metadata in one pass across selected files.</p>
      </div>

      <div className="studio-tabs">
        <button type="button" className={activeTab === "core" ? "tab-btn active" : "tab-btn"} onClick={() => setActiveTab("core")}>Core</button>
        <button type="button" className={activeTab === "text" ? "tab-btn active" : "tab-btn"} onClick={() => setActiveTab("text")}>Text</button>
        <button type="button" className={activeTab === "location" ? "tab-btn active" : "tab-btn"} onClick={() => setActiveTab("location")}>Location</button>
        <button type="button" className={activeTab === "contact" ? "tab-btn active" : "tab-btn"} onClick={() => setActiveTab("contact")}>Contact</button>
        <button type="button" className={activeTab === "rename" ? "tab-btn active" : "tab-btn"} onClick={() => setActiveTab("rename")}>Rename</button>
        <button type="button" className={activeTab === "advanced" ? "tab-btn active" : "tab-btn"} onClick={() => setActiveTab("advanced")}>Advanced</button>
      </div>

      {activeTab === "core" ? <div className="grid">
        <label>
          Date Taken
          <DatePicker
            selected={exifToDate(value.date_taken)}
            onChange={(date) => onChange({ ...value, date_taken: dateToExif(date) })}
            showTimeSelect
            dateFormat="MMM d, yyyy h:mm aa"
            className="datepicker-input"
            calendarClassName="modern-datepicker"
            popperClassName="datepicker-popper"
            portalId="root"
            showPopperArrow={false}
            placeholderText="Select capture date and time"
          />
        </label>
        <label>
          Title
          <input type="text" value={value.title ?? ""} onChange={update("title")} />
        </label>
        <label>
          Headline
          <input type="text" value={value.headline ?? ""} onChange={update("headline")} />
        </label>
        <label>
          Artist / Creator
          <input type="text" value={value.artist ?? ""} onChange={update("artist")} />
        </label>
        <label>
          Credit
          <input type="text" value={value.credit ?? ""} onChange={update("credit")} />
        </label>
        <label>
          Source
          <input type="text" value={value.source ?? ""} onChange={update("source")} />
        </label>
        <label>
          Copyright
          <input type="text" value={value.copyright_text ?? ""} onChange={update("copyright_text")} />
        </label>
        <label>
          Rating (0-5)
          <input type="number" min="0" max="5" value={value.rating ?? ""} onChange={updateNumber("rating")} />
        </label>
      </div> : null}

      {activeTab === "text" ? <div className="grid" style={{ marginTop: "12px" }}>
        <label className="wide-field">
          Description
          <textarea rows="3" value={value.description ?? ""} onChange={update("description")} />
        </label>
        <label className="wide-field">
          Comment
          <textarea rows="3" value={value.comment ?? ""} onChange={update("comment")} />
        </label>
        <label className="wide-field">
          Keywords (comma separated)
          <input
            type="text"
            value={value.keywords.join(", ")}
            onChange={(event) => onChange({ ...value, keywords: splitKeywords(event.target.value) })}
          />
        </label>
        <label className="wide-field">
          Special Instructions
          <textarea rows="2" value={value.instructions ?? ""} onChange={update("instructions")} />
        </label>
      </div> : null}

      {activeTab === "location" ? <>
      <h3 className="meta-subhead">Location Metadata</h3>
      <div className="grid">
        <label>
          GPS Latitude
          <input type="number" step="0.000001" value={value.gps_latitude ?? ""} onChange={updateNumber("gps_latitude")} />
        </label>
        <label>
          GPS Longitude
          <input type="number" step="0.000001" value={value.gps_longitude ?? ""} onChange={updateNumber("gps_longitude")} />
        </label>
        <label>
          Location Name
          <input type="text" value={value.location_name ?? ""} onChange={update("location_name")} />
        </label>
        <label>
          City
          <input type="text" value={value.city ?? ""} onChange={update("city")} />
        </label>
        <label>
          State / Province
          <input type="text" value={value.state ?? ""} onChange={update("state")} />
        </label>
        <label>
          Country
          <input type="text" value={value.country ?? ""} onChange={update("country")} />
        </label>
        <label>
          Country Code
          <input type="text" value={value.country_code ?? ""} onChange={update("country_code")} />
        </label>
        <label>
          Postal Code
          <input type="text" value={value.postal_code ?? ""} onChange={update("postal_code")} />
        </label>
      </div>

      <div className="row" style={{ marginTop: "12px" }}>
        <input
          type="text"
          placeholder="Paste Google Maps link to auto-fill GPS"
          value={mapLink}
          onChange={(event) => setMapLink(event.target.value)}
        />
        <button type="button" className="btn-accent" onClick={applyMapCoordinates}>
          <FiMapPin />
          Use Map Coordinates
        </button>
      </div>
      <p className="muted">Supports links containing @lat,long or !3dlat!4dlong.</p>
      </> : null}

      {activeTab === "contact" ? <>
      <h3 className="meta-subhead">Contact + Technical</h3>
      <div className="grid">
        <label>
          Contact Email
          <input type="email" value={value.contact_email ?? ""} onChange={update("contact_email")} />
        </label>
        <label>
          Contact URL
          <input type="url" value={value.contact_url ?? ""} onChange={update("contact_url")} />
        </label>
        <label>
          Software
          <input type="text" value={value.software ?? ""} onChange={update("software")} />
        </label>
      </div>
      </> : null}

      {activeTab === "rename" ? <>
      <h3 className="meta-subhead">Filename Rename</h3>
      <div className="grid">
        <label className="wide-field">
          Filename Prefix
          <input
            type="text"
            placeholder="TrackTech x 450 x 450"
            value={renamePrefix}
            onChange={(event) => onRenamePrefixChange(event.target.value)}
          />
        </label>
        <label>
          Start Number
          <input
            type="number"
            min="1"
            step="1"
            value={renameStartIndex}
            onChange={(event) => {
              const raw = event.target.value.trim();
              if (!raw) {
                onRenameStartIndexChange(1);
                return;
              }
              const parsed = Number(raw);
              onRenameStartIndexChange(Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 1);
            }}
          />
        </label>
        <label>
          Number Position
          <select
            value={position}
            onChange={(event) => onRenameNumberPositionChange(event.target.value === "prefix" ? "prefix" : "suffix")}
          >
            <option value="suffix">Suffix (ABC x 457 - 1)</option>
            <option value="prefix">Prefix (1 - ABC x 457)</option>
          </select>
        </label>
        <div className="rename-preview-box wide-field">
          <p className="preview-label">Pattern Preview</p>
          <p>{previewLine(previewStart)}</p>
          <p>{previewLine(previewStart + 1)}</p>
          <p>{previewLine(previewStart + 2)}</p>
          <p className="muted">File extensions stay unchanged (for example .jpeg, .png).</p>
        </div>
      </div>
      </> : null}

      {activeTab === "advanced" ? <details className="advanced-meta" open>
        <summary>Advanced Custom Fields (key=value per line)</summary>
        <textarea
          rows="5"
          value={customFieldText}
          onChange={(event) => {
            const next = event.target.value;
            setCustomFieldText(next);
            onChange({ ...value, custom_fields: csvToCustomFields(next) });
          }}
        />
      </details> : null}

      <div className="mode-switch">
        <span>Write Mode</span>
        <div className="mode-toggle" role="tablist" aria-label="Write mode">
          <button
            type="button"
            className={writeMode === "overwrite" ? "mode-btn active" : "mode-btn"}
            onClick={() => onWriteModeChange("overwrite")}
          >
            Overwrite Originals
          </button>
          <button
            type="button"
            className={writeMode === "output_folder" ? "mode-btn active" : "mode-btn"}
            onClick={() => onWriteModeChange("output_folder")}
          >
            Write to Output Folder
          </button>
        </div>
      </div>

      <section className="inline-start-box">
        <div className="row between">
          <h3 className="title-with-icon"><FiPlayCircle /> Start Processing</h3>
          <button className="btn-primary" type="button" disabled={!canStart} onClick={onStartProcessing}>
            <FiPlayCircle /> Start Metadata Job
          </button>
        </div>
      </section>
    </section>
  );
}
