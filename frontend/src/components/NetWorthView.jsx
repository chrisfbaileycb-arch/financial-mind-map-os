import { useEffect, useState } from 'react'
import { api } from '../api.js'

const BUCKET_META = {
  BUCKET_TAX: { label: 'Tax-deferred', hint: 'IRA, 401(k), HSA', color: '#4A90D9' },
  BUCKET_TAXABLE: { label: 'Taxable', hint: 'Checking, Savings, Brokerage', color: '#E8A838' },
  BUCKET_FREE: { label: 'Tax-free', hint: 'Roth IRA, 529, Muni', color: '#50C878' },
  UNBUCKETED: { label: 'Unbucketed', hint: 'No bucket set', color: '#9B9B9B' },
}

export default function NetWorthView() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.networth().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="view"><div className="error-banner">{error}</div></div>
  if (!data) return <div className="view"><p className="muted">Loading…</p></div>

  const { total, by_bucket } = data.summary
  const history = data.history
  const histMax = Math.max(1, ...history.map((h) => h.total))
  const fmt = (n) => `$${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`

  return (
    <div className="view">
      <h2>Net Worth</h2>
      <div className="networth-total">{fmt(total)}</div>

      <div className="bucket-cards">
        {Object.entries(BUCKET_META).map(([key, meta]) =>
          by_bucket[key] !== undefined ? (
            <div className="bucket-card" key={key} style={{ borderTopColor: meta.color }}>
              <div className="bucket-amount">{fmt(by_bucket[key])}</div>
              <div className="bucket-name">{meta.label}</div>
              <div className="bucket-hint muted">{meta.hint}</div>
            </div>
          ) : null,
        )}
      </div>

      <h3>Net worth over time</h3>
      <div className="bars">
        {history.length === 0 && <p className="muted">Run a sync to start tracking.</p>}
        {history.map((h) => (
          <div className="bar-row" key={h.date}>
            <span className="bar-label">{h.date}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(h.total / histMax) * 100}%` }} />
            </div>
            <span className="bar-value">{fmt(h.total)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
