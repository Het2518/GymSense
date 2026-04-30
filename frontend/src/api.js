// === FILE: src/api.js ===
// GymSense AI — API client with Auth

const API_BASE = import.meta.env.VITE_API_URL || '';

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

// --- Auth Endpoints ---

export async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email); // OAuth2PasswordBearer uses 'username'
  formData.append('password', password);

  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString()
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(err.detail);
  }
  return response.json();
}

export async function register(name, email, password) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password })
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail);
  }
  return response.json();
}

export async function getMe() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Not authenticated');
  return response.json();
}

export async function updateProfile(profileData) {
  const response = await fetch(`${API_BASE}/api/auth/profile`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(profileData)
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to update profile' }));
    throw new Error(err.detail);
  }
  return response.json();
}

// --- App Endpoints ---

export async function analyzeSession(file, coachFocus) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('coach_focus', coachFocus || 'general');

  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: getAuthHeaders(true),
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function getReport(sessionId) {
  const response = await fetch(`${API_BASE}/api/report/${sessionId}`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Report not found');
  return response.blob();
}

export async function getSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Failed to fetch sessions');
  return response.json();
}

export async function getDashboardStats() {
  const response = await fetch(`${API_BASE}/api/dashboard/stats`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error('Backend unreachable');
  return response.json();
}

export async function getSessionDetail(sessionId) {
  console.log(`[API] getSessionDetail: ${sessionId}`);
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Session not found');
  return response.json();
}

export async function getGoals() {
  const response = await fetch(`${API_BASE}/api/goals`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Failed to fetch goals');
  return response.json();
}

export async function saveGoal(goalData) {
  const response = await fetch(`${API_BASE}/api/goals`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(goalData)
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to save goal' }));
    throw new Error(err.detail);
  }
  return response.json();
}

export async function updateGoal(goalId, goalData) {
  const response = await fetch(`${API_BASE}/api/goals/${goalId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(goalData)
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Failed to update goal' }));
    throw new Error(err.detail);
  }
  return response.json();
}

export async function deleteGoal(goalId) {
  const response = await fetch(`${API_BASE}/api/goals/${goalId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error('Failed to delete goal');
  return response.json();
}

