import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'

const BUCKET_META = {
  BUCKET_TAX: { label: 'Tax-deferred', hint: 'IRA, 401(k), HSA', color: '#4A90D9' },
  BUCKET_TAXABLE: { label: 'Taxable', hint: 'Checking, Savings, Brokerage', color: '#E8A838' },
  BUCKET_FREE: { label: 'Tax-free', hint: 'Roth IRA, 529, Muni', color: '#50C878' },
  UNBUCKETED: { label: 'Unbucketed', hint: 'No bucket set', color: '#9B9B9B' },
}

export default function NetWorthView() {
  const [data, setData] = useState(null)
  const [holdings, setHoldings] = useState([])
  const [accounts, setAccounts] = useState([])
  const [error, setError] = useState(null)
  const [refreshNote, setRefreshNote] = useState(null)

  const reload = useCallback(() => {
    api.networth().then(setData).catch((e) => setError(e.message))
    api.holdings().then(setHoldings).catch((e) => setError(e.message))
    api.accounts().then(setAccounts).catch((e) => setError(e.message))
  }, [])

  useEffect(() => { reload() }, [reload])

  if (error) return <div className="view"><div className="error-banner">{error}</div></div>
  if (!data) return <div className="view"><p className="muted">Loading…</p></div>

  const { total, by_bucket } = data.summary
  const history = data.history
  const histMax = Math.max(1, ...history.map((h) => h.total))
  const fmt = (n) => `$${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
  const fmt2 = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

  const refresh = () => {
    setRefreshNote('Refreshing…')
    api.refreshPrices()
      .then((r) => {
        if (r.provider === 'none') {
          setRefreshNote('No market-data provider configured — set FMM_FINNHUB_API_KEY (or Alpha Vantage) in .env to fetch live prices.')
        } else {
          setRefreshNote(`Updated ${r.updated} symbol(s) via ${r.provider}.`)
          reload()
        }
      })
      .catch((e) => setRefreshNote(`Refresh failed: ${e.message}`))
  }

  const addHolding = (e) => {
    e.preventDefault()
    const f = e.target
    const body = {
      account_hash: f.account.value,
      symbol: f.symbol.value.trim(),
      quantity: parseFloat(f.quantity.value),
      cost_basis: f.cost_basis.value ? parseFloat(f.cost_basis.value) : null,
      last_price: f.last_price.value ? parseFloat(f.last_price.value) : null,
      label: f.label.value.trim() || null,
    }
    if (!body.account_hash || !body.symbol || !body.quantity) return
    api.createHolding(body).then(() => { f.reset(); reload() }).catch((e2) => setError(e2.message))
  }

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

      <h3>
        Holdings{' '}
        <button className="btn ghost small" onClick={refresh}>Refresh prices</button>
      </h3>
      {refreshNote && <p className="muted">{refreshNote}</p>}
      {holdings.length === 0 && <p className="muted">No holdings yet — add one below.</p>}
      {holdings.length > 0 && (
        <ul className="mini-list">
          {holdings.map((h) => (
            <li key={h.id}>
              <strong>{h.symbol}</strong>
              {h.label ? ` — ${h.label}` : ''} · {h.account_name || 'unknown account'}
              {' · '}{h.quantity} × {fmt2(h.last_price || h.cost_basis)} ={' '}
              <strong>{fmt2(h.market_value)}</strong>
              {h.gain !== null && (
                <span style={{ color: h.gain >= 0 ? '#50C878' : '#E05656' }}>
                  {' '}({h.gain >= 0 ? '+' : ''}{fmt2(h.gain)})
                </span>
              )}
              {h.last_price_at && (
                <span className="muted"> as of {h.last_price_at.slice(0, 16).replace('T', ' ')}</span>
              )}
              <button className="btn ghost small" onClick={() => api.deleteHolding(h.id).then(reload)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <form className="add-form" onSubmit={addHolding}>
        <select name="account" defaultValue="">
          <option value="" disabled>Account…</option>
          {accounts.map((a) => (
            <option key={a.account_hash} value={a.account_hash}>{a.name}</option>
          ))}
        </select>
        <input name="symbol" placeholder="Symbol (VTI)" />
        <input name="quantity" type="number" step="any" min="0" placeholder="Qty" className="inline-num" />
        <input name="cost_basis" type="number" step="any" min="0" placeholder="Cost/share" className="inline-num" />
        <input name="last_price" type="number" step="any" min="0" placeholder="Price (optional)" className="inline-num" />
        <input name="label" placeholder="Label (optional)" />
        <button className="btn primary small" type="submit">Add holding</button>
      </form>

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
