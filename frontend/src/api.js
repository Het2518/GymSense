// === FILE: src/api.js ===
// GymSense AI — API client

const RENDER_URL = 'https://gymsense-j.onrender.com';
const API_BASE = import.meta.env.VITE_API_URL
  || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? RENDER_URL : '');

console.log(`[API] Backend Base URL: ${API_BASE || 'relative proxy (dev)'}`);

function getAuthHeaders(isFormData = false) {
  const token = localStorage.getItem('gymsense_token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
}

// Global fetch wrapper for comprehensive logging
async function doFetch(endpoint, options = {}, expectBlob = false) {
  const url = `${API_BASE}${endpoint}`;
  const method = options.method || 'GET';
  
  // Log request
  console.log(`[API REQUEST] ${method} ${endpoint}`, options.body instanceof FormData ? '(FormData)' : (options.body || ''));

  let response;
  try {
    response = await fetch(url, options);
  } catch (err) {
    console.error(`[API NETWORK ERROR] ${method} ${endpoint} =>`, err);
    throw err;
  }

  if (!response.ok) {
    const errorText = await response.text();
    console.error(`[API ERROR] ${method} ${endpoint} => HTTP ${response.status}\nRaw Error Text:`, errorText);
    let detail = `HTTP ${response.status}`;
    try {
      const errObj = JSON.parse(errorText);
      detail = errObj.detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }

  if (expectBlob) {
    const blob = await response.blob();
    console.log(`[API SUCCESS] ${method} ${endpoint} => Blob(size: ${blob.size})`);
    return blob;
  }

  const data = await response.json();
  console.log(`[API SUCCESS] ${method} ${endpoint} =>`, data);
  return data;
}

// --- Auth Endpoints ---

export async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email); // OAuth2PasswordBearer uses 'username'
  formData.append('password', password);

  return doFetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString()
  });
}

export async function register(name, email, password) {
  return doFetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password })
  });
}

export async function getMe() {
  return doFetch('/api/auth/me', {
    headers: getAuthHeaders()
  });
}

export async function updateProfile(profileData) {
  return doFetch('/api/auth/profile', {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(profileData)
  });
}

// --- App Endpoints ---

export async function analyzeSession(file, coachFocus) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('coach_focus', coachFocus || 'general');

  return doFetch('/api/analyze', {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: formData,
  });
}

export async function getReport(sessionId) {
  return doFetch(`/api/report/${sessionId}`, {
    headers: getAuthHeaders()
  }, true); // expectBlob = true
}

export async function getSessions() {
  return doFetch('/api/sessions', {
    headers: getAuthHeaders()
  });
}

export async function getDashboardStats() {
  return doFetch('/api/dashboard/stats', {
    headers: getAuthHeaders()
  });
}

export async function checkHealth() {
  return doFetch('/api/health');
}

export async function getSessionDetail(sessionId) {
  return doFetch(`/api/sessions/${sessionId}`, {
    headers: getAuthHeaders()
  });
}

export async function getGoals() {
  return doFetch('/api/goals', {
    headers: getAuthHeaders()
  });
}

export async function saveGoal(goalData) {
  return doFetch('/api/goals', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(goalData)
  });
}

export async function updateGoal(goalId, goalData) {
  return doFetch(`/api/goals/${goalId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(goalData)
  });
}

export async function deleteGoal(goalId) {
  return doFetch(`/api/goals/${goalId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
}

