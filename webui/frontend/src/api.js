const API_BASE = '/api';

async function fetchJSON(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  getStatus: () => fetchJSON('/status'),
  getProgress: () => fetchJSON('/progress'),
  getGraph: () => fetchJSON('/graph?with_edges=true'),
  getModels: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchJSON(`/models${qs ? '?' + qs : ''}`);
  },
  getModel: (hash) => fetchJSON(`/models/${hash}`),
  getHistory: (hash) => fetchJSON(`/history/${hash}`),
  getLogs: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetchJSON(`/logs${qs ? '?' + qs : ''}`);
  },
  getPlans: () => fetchJSON('/plans'),
  getPlan: (name) => fetchJSON(`/plans/${name}`),
  getSchema: () => fetchJSON('/schema'),
  startRun: (data) => fetchJSON('/run', { method: 'POST', body: JSON.stringify(data) }),
  createBranch: (data) => fetchJSON('/branch', { method: 'POST', body: JSON.stringify(data) }),
  mergeBranch: (data) => fetchJSON('/merge', { method: 'POST', body: JSON.stringify(data) }),
};
