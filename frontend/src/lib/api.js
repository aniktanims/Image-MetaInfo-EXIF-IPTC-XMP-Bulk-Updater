const API_BASE = "http://localhost:8000";

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
  const socket = new WebSocket(`ws://localhost:8000/ws/jobs/${jobId}`);
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  return socket;
}
