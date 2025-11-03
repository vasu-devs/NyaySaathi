export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

function altBase(base) {
  try {
    const u = new URL(base);
    if (u.hostname === "localhost") {
      u.hostname = "127.0.0.1";
      return u.toString().replace(/\/$/, "");
    }
    if (u.hostname === "127.0.0.1") {
      u.hostname = "localhost";
      return u.toString().replace(/\/$/, "");
    }
  } catch {
    // ignore URL parse errors
  }
  return null;
}

// Simple token store
export function setToken(t) {
  if (t) localStorage.setItem("nyay_token", t); else localStorage.removeItem("nyay_token");
}
export function getToken() {
  return localStorage.getItem("nyay_token");
}

export function streamChat(query, onToken, onEnd) {
  const mkUrl = (base) => `${base}/chat/stream?query=${encodeURIComponent(query)}`;
  const alt = altBase(API_BASE);
  let es = null;
  let triedAlt = false;
  const start = (base) => {
    es = new EventSource(mkUrl(base), { withCredentials: false });
    es.addEventListener("token", (e) => onToken && onToken(e.data));
    es.addEventListener("end", () => { es.close(); onEnd && onEnd(); });
    es.onerror = () => {
      es.close();
      if (!triedAlt && alt && alt !== base) { triedAlt = true; start(alt); return; }
      onEnd && onEnd();
    };
  };
  start(API_BASE);
  return () => { try { es && es.close(); } catch { /* ignore */ } };
}

export async function askOnce(query) {
  async function attempt(base) {
    const res = await fetch(`${base}/chat/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.answer;
  }
  async function attemptGet(base) {
    const res = await fetch(`${base}/chat/ask?query=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.answer;
  }
  try {
    return await attempt(API_BASE);
  } catch (e) {
    const alt = altBase(API_BASE);
    try {
      if (alt) return await attempt(alt);
  } catch { /* ignore and continue */ }
    // Fallback to GET variant
    try {
      return await attemptGet(API_BASE);
  } catch { /* ignore and continue */ }
    if (alt) return await attemptGet(alt);
    throw e;
  }
}

export async function debugRetrieve(query, topK = 6) {
  let url = `${API_BASE}/chat/debug/retrieve?query=${encodeURIComponent(query)}&top_k=${encodeURIComponent(topK)}`;
  let res = await fetch(url);
  if (!res.ok) {
    const alt = altBase(API_BASE);
    if (alt) {
      url = `${alt}/chat/debug/retrieve?query=${encodeURIComponent(query)}&top_k=${encodeURIComponent(topK)}`;
      res = await fetch(url);
    }
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function uploadDocument(file, title) {
  const fd = new FormData();
  fd.append("file", file);
  if (title) fd.append("title", title);
  const res = await fetch(`${API_BASE}/admin/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${getToken()}` },
    body: fd,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Admin upload with real-time progress
export function uploadDocumentWithProgress(file, title, onProgress) {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/admin/documents`);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        onProgress(pct);
      }
    };
    xhr.upload.onload = () => {
      if (onProgress) onProgress(100);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response);
      } else {
        const detail = (xhr.response && (xhr.response.detail || xhr.response.message)) || xhr.statusText || `HTTP ${xhr.status}`;
        const err = new Error(detail);
        err.status = xhr.status;
        err.body = xhr.response;
        reject(err);
      }
    };
    xhr.onerror = () => reject(new Error("Network error"));
    xhr.send(fd);
  });
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE}/admin/documents`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function approveDocument(docId) {
  const res = await fetch(`${API_BASE}/admin/documents/${encodeURIComponent(docId)}/approve`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function unapproveDocument(docId) {
  const res = await fetch(`${API_BASE}/admin/documents/${encodeURIComponent(docId)}/unapprove`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${API_BASE}/admin/documents/${encodeURIComponent(docId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// NyayLens
export function lensUpload(file, title, onProgress) {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/nyaylens/upload`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        onProgress(pct);
      }
    };
    xhr.upload.onload = () => {
      if (onProgress) onProgress(100);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response);
      } else {
        reject(new Error(`HTTP ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("Network error"));
    xhr.send(fd);
  });
}

export function streamLens(lensId, query, onToken, onEnd) {
  const url = `${API_BASE}/nyaylens/${encodeURIComponent(lensId)}/stream?query=${encodeURIComponent(query)}`;
  const es = new EventSource(url);
  es.addEventListener("token", (e) => onToken && onToken(e.data));
  es.addEventListener("end", () => { es.close(); onEnd && onEnd(); });
  es.onerror = () => { es.close(); onEnd && onEnd(); };
  return () => es.close();
}

export async function getLensStatus(lensId) {
  const res = await fetch(`${API_BASE}/nyaylens/${encodeURIComponent(lensId)}/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// NyayShala
export async function getDailyNyayShala(field, random = false) {
  const params = new URLSearchParams();
  if (field) params.set("field", field);
  if (random) params.set("random", "1");
  const url = params.toString() ? `${API_BASE}/nyayshala/daily?${params.toString()}` : `${API_BASE}/nyayshala/daily`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Connectivity check (bypasses API_BASE because health is at root)
export async function pingHealth(base = "http://localhost:8000") {
  const res = await fetch(`${base}/health/live`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Public client configuration
export async function getClientConfig() {
  const res = await fetch(`${API_BASE}/client-config`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
