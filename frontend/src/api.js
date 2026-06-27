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
  importCsv: (payload) =>
    request('/import/csv', { method: 'POST', body: JSON.stringify(payload) }),

  // Collections
  accounts: () => request('/accounts'),
  bills: () => request('/bills'),
  members: () => request('/members'),
  subscriptions: () => request('/subscriptions'),
  transactions: ({ limit = 200, q = '', category = '' } = {}) => {
    const p = new URLSearchParams({ limit })
    if (q) p.set('q', q)
    if (category) p.set('category', category)
    return request(`/transactions?${p.toString()}`)
  },
  spending: () => request('/spending'),
  networth: () => request('/networth'),
  cashflow: () => request('/cashflow'),
  budgets: () => request('/budgets'),
  goals: () => request('/goals'),

  // Create
  createAccount: (b) => request('/accounts', { method: 'POST', body: JSON.stringify(b) }),
  createBill: (b) => request('/bills', { method: 'POST', body: JSON.stringify(b) }),
  createMember: (b) => request('/members', { method: 'POST', body: JSON.stringify(b) }),
  createSchedule: (b) =>
    request('/paycheck-schedules', { method: 'POST', body: JSON.stringify(b) }),

  // Edit
  updateAccount: (hash, b) =>
    request(`/accounts/${hash}`, { method: 'PATCH', body: JSON.stringify(b) }),
  updateBill: (id, b) =>
    request(`/bills/${id}`, { method: 'PATCH', body: JSON.stringify(b) }),
  deleteBill: (id) => request(`/bills/${id}`, { method: 'DELETE' }),
  updateTransaction: (id, b) =>
    request(`/transactions/${id}`, { method: 'PATCH', body: JSON.stringify(b) }),
  splitTransaction: (id, parts) =>
    request(`/transactions/${id}/split`, {
      method: 'POST',
      body: JSON.stringify({ parts }),
    }),

  // Budgets & goals
  upsertBudget: (b) => request('/budgets', { method: 'PUT', body: JSON.stringify(b) }),
  deleteBudget: (cat) => request(`/budgets/${encodeURIComponent(cat)}`, { method: 'DELETE' }),
  createGoal: (b) => request('/goals', { method: 'POST', body: JSON.stringify(b) }),
  updateGoal: (id, b) =>
    request(`/goals/${id}`, { method: 'PATCH', body: JSON.stringify(b) }),
  deleteGoal: (id) => request(`/goals/${id}`, { method: 'DELETE' }),
}
