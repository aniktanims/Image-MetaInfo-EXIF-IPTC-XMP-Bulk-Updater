function resolveApiBase() {
  const envBase = import.meta.env.VITE_API_BASE;
  if (envBase) {
    return envBase.replace(/\/$/, "");
  }

  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }

  const { protocol, hostname, host, port } = window.location;

  // Vite dev server usually runs on 5173 and talks to backend on 8000.
  if (port === "5173") {
    return `${protocol}//${hostname}:8000`;
  }

  // Packaged/runtime mode serves frontend from backend origin directly.
  return `${protocol}//${host}`;
}

function resolveWsBase(apiBase) {
  const envWs = import.meta.env.VITE_WS_BASE;
  if (envWs) {
    return envWs.replace(/\/$/, "");
  }

  if (apiBase.startsWith("http://") || apiBase.startsWith("https://")) {
    return apiBase.replace(/^http/, "ws");
  }

  if (typeof window === "undefined") {
    return "ws://127.0.0.1:8000";
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${wsProtocol}://${window.location.host}`;
}

const API_BASE = resolveApiBase();
const WS_BASE = resolveWsBase(API_BASE);

export async function selectFolder() {
  const response = await fetch(`${API_BASE}/api/scan/select-folder`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Folder selection failed");
  }
  return response.json();
}

export async function scanFolder(folderPath) {
  const response = await fetch(`${API_BASE}/api/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Scan failed");
  }
  return response.json();
}

export async function validateFolder(folderPath) {
  const response = await fetch(`${API_BASE}/api/scan/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Validation failed");
  }
  return response.json();
}

export async function getSystemMetrics() {
  const response = await fetch(`${API_BASE}/api/system/metrics`);
  if (!response.ok) {
    throw new Error("Failed to load system metrics");
  }
  return response.json();
}

export async function createJob(payload) {
  const response = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create job");
  }
  return response.json();
}

export async function getJob(jobId) {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get job");
  }
  return response.json();
}

export async function cancelJob(jobId) {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to cancel job");
  }
}

export function openJobSocket(jobId, onMessage) {
  const socket = new WebSocket(`${WS_BASE}/ws/jobs/${jobId}`);
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  return socket;
}
