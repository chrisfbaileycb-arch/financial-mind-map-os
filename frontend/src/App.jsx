import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import MindMap from './components/MindMap.jsx'
import ActionInbox from './components/ActionInbox.jsx'
import ImportPanel from './components/ImportPanel.jsx'
import TransactionsView from './components/TransactionsView.jsx'
import SpendingView from './components/SpendingView.jsx'
import ManageView from './components/ManageView.jsx'

const VIEWS = [
  { key: 'map', label: 'Map' },
  { key: 'transactions', label: 'Transactions' },
  { key: 'spending', label: 'Spending' },
  { key: 'manage', label: 'Manage' },
]

export default function App() {
  const [view, setView] = useState('map')
  const [graph, setGraph] = useState(null)
  const [report, setReport] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const [importOpen, setImportOpen] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [g, r] = await Promise.all([api.graph(), api.latestReport()])
      setGraph(g)
      setReport(r.report)
      setItems(r.items)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const runSync = async () => {
    setLoading(true)
    setError(null)
    try {
      await api.sync()
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const resolve = async (id, resolution) => {
    try {
      await api.resolveItem(id, resolution)
      setItems((prev) =>
        prev.map((it) => (it.id === id ? { ...it, status: resolution } : it)),
      )
      // Refresh the graph so a cancelled subscription drops off the map.
      api.graph().then(setGraph).catch(() => {})
    } catch (e) {
      setError(e.message)
    }
  }

  const pending = items.filter((it) => it.status === 'PENDING')

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◈</span>
          <span>Financial Mind-Map OS</span>
        </div>
        <nav className="nav">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              className={`nav-btn ${view === v.key ? 'active' : ''}`}
              onClick={() => setView(v.key)}
            >
              {v.label}
            </button>
          ))}
        </nav>
        <div className="actions">
          <button className="btn ghost" onClick={() => setImportOpen(true)}>
            Import CSV
          </button>
          {view === 'map' && (
            <button className="btn ghost" onClick={() => setPanelOpen((o) => !o)}>
              {panelOpen ? 'Hide' : 'Actions'}{pending.length ? ` (${pending.length})` : ''}
            </button>
          )}
          <button className="btn primary" onClick={runSync} disabled={loading}>
            {loading ? 'Syncing…' : 'Run Sync'}
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {view === 'map' && (
        <div className="layout">
          <main className="map-area">
            {graph ? (
              <MindMap graph={graph} />
            ) : (
              <div className="placeholder">Loading your financial map…</div>
            )}
          </main>
          {panelOpen && (
            <aside className="side-panel">
              <ActionInbox report={report} items={items} onResolve={resolve} />
            </aside>
          )}
        </div>
      )}

      {view === 'transactions' && <TransactionsView />}
      {view === 'spending' && <SpendingView />}
      {view === 'manage' && <ManageView />}

      {importOpen && (
        <ImportPanel
          onClose={() => setImportOpen(false)}
          onImported={() => { load(); setImportOpen(false) }}
        />
      )}
    </div>
  )
}
