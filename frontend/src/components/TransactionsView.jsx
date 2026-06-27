import { useEffect, useState } from 'react'
import { api } from '../api.js'

function SplitModal({ txn, onClose, onDone }) {
  const half = Math.round((txn.amount / 2) * 100) / 100
  const [parts, setParts] = useState([
    { amount: half, category: '' },
    { amount: Math.round((txn.amount - half) * 100) / 100, category: '' },
  ])
  const [error, setError] = useState(null)

  const total = parts.reduce((s, p) => s + Number(p.amount || 0), 0)
  const setPart = (i, field, val) =>
    setParts(parts.map((p, j) => (j === i ? { ...p, [field]: val } : p)))

  const submit = async () => {
    try {
      await api.splitTransaction(
        txn.id,
        parts.map((p) => ({ amount: Number(p.amount), category: p.category || null })),
      )
      onDone()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Split transaction</h2>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>
        <p className="muted small">Original: {txn.amount} ({txn.description_tokens || '—'})</p>
        {parts.map((p, i) => (
          <div className="grid" key={i}>
            <label className="field">
              <span>Amount</span>
              <input type="number" step="0.01" value={p.amount}
                onChange={(e) => setPart(i, 'amount', e.target.value)} />
            </label>
            <label className="field">
              <span>Category</span>
              <input type="text" value={p.category}
                onChange={(e) => setPart(i, 'category', e.target.value)} />
            </label>
          </div>
        ))}
        <div className="row-between">
          <button className="btn ghost" onClick={() => setParts([...parts, { amount: 0, category: '' }])}>
            + part
          </button>
          <span className={`muted small ${Math.abs(total - txn.amount) > 0.001 ? 'warn' : ''}`}>
            Sum: {total.toFixed(2)} / {txn.amount}
          </span>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="modal-foot">
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={submit}>Split</button>
        </div>
      </div>
    </div>
  )
}

export default function TransactionsView() {
  const [txns, setTxns] = useState([])
  const [splitting, setSplitting] = useState(null)
  const [error, setError] = useState(null)

  const load = () => api.transactions().then(setTxns).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const saveCategory = async (id, category) => {
    try {
      await api.updateTransaction(id, { category })
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="view">
      <h2>Transactions</h2>
      {error && <div className="error-banner">{error}</div>}
      <table className="data-table">
        <thead>
          <tr><th>Date</th><th>Description</th><th className="num">Amount</th><th>Category</th><th></th></tr>
        </thead>
        <tbody>
          {txns.map((t) => (
            <tr key={t.id}>
              <td>{t.date}</td>
              <td className="muted">{t.description_tokens || '—'}</td>
              <td className={`num ${t.amount < 0 ? 'neg' : 'pos'}`}>{t.amount.toFixed(2)}</td>
              <td>
                <input
                  className="cat-input"
                  defaultValue={t.category || ''}
                  placeholder="—"
                  onBlur={(e) => saveCategory(t.id, e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
                />
              </td>
              <td>
                {t.amount < 0 && (
                  <button className="btn ghost small" onClick={() => setSplitting(t)}>Split</button>
                )}
              </td>
            </tr>
          ))}
          {txns.length === 0 && (
            <tr><td colSpan={5} className="muted empty">No transactions yet — import a CSV.</td></tr>
          )}
        </tbody>
      </table>
      {splitting && (
        <SplitModal
          txn={splitting}
          onClose={() => setSplitting(null)}
          onDone={() => { setSplitting(null); load() }}
        />
      )}
    </div>
  )
}
