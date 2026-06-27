// Thin client for the Financial Mind-Map OS API.

async function request(path, options) {
  const resp = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const detail = await resp.text()
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`)
  }
  return resp.json()
}

export const api = {
  health: () => request('/health'),
  sync: () => request('/sync', { method: 'POST' }),
  latestReport: () => request('/report/latest'),
  graph: () => request('/graph'),
  resolveItem: (id, resolution, snoozeDays = 7) =>
    request(`/items/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution, snooze_days: snoozeDays }),
    }),
  accounts: () => request('/accounts'),
  importCsv: (payload) =>
    request('/import/csv', { method: 'POST', body: JSON.stringify(payload) }),
}
