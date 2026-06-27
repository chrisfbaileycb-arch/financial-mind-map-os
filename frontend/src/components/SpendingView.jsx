import { useEffect, useState } from 'react'
import { api } from '../api.js'

function Bars({ title, rows, labelKey, max }) {
  return (
    <div className="bars">
      <h3>{title}</h3>
      {rows.length === 0 && <p className="muted">No spending yet.</p>}
      {rows.map((r) => (
        <div className="bar-row" key={r[labelKey]}>
          <span className="bar-label">{r[labelKey]}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${max ? (r.spent / max) * 100 : 0}%` }} />
          </div>
          <span className="bar-value">${r.spent.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

function Budgets({ budgets }) {
  if (budgets.length === 0) {
    return (
      <div className="bars">
        <h3>Budgets</h3>
        <p className="muted">No budgets yet — add some in Manage.</p>
      </div>
    )
  }
  return (
    <div className="bars">
      <h3>Budgets (this month)</h3>
      {budgets.map((b) => {
        const pct = b.monthly_limit ? (b.spent / b.monthly_limit) * 100 : 0
        const over = b.spent > b.monthly_limit
        return (
          <div className="bar-row" key={b.category}>
            <span className="bar-label">{b.category}</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${Math.min(100, pct)}%`, background: over ? '#d0021b' : '#50c878' }}
              />
            </div>
            <span className="bar-value">
              ${Number(b.spent).toLocaleString()} / ${Number(b.monthly_limit).toLocaleString()}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function SpendingView() {
  const [data, setData] = useState({ by_month: [], by_category: [] })
  const [budgets, setBudgets] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api.spending().then(setData).catch((e) => setError(e.message))
    api.budgets().then(setBudgets).catch(() => {})
  }, [])

  const months = [...data.by_month].reverse() // oldest -> newest
  const monthMax = Math.max(1, ...months.map((m) => m.spent))
  const catMax = Math.max(1, ...data.by_category.map((c) => c.spent))

  return (
    <div className="view">
      <h2>Spending</h2>
      {error && <div className="error-banner">{error}</div>}
      <div className="spending-grid">
        <Bars title="By month" rows={months} labelKey="month" max={monthMax} />
        <Bars title="By category" rows={data.by_category} labelKey="category" max={catMax} />
      </div>
      <Budgets budgets={budgets} />
    </div>
  )
}
