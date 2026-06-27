import { useEffect, useState } from 'react'
import { api } from '../api.js'

const fmt = (n) =>
  `${n < 0 ? '-' : ''}$${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 2 })}`

export default function CashFlowView() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.cashflow().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="view"><div className="error-banner">{error}</div></div>
  if (!data) return <div className="view"><p className="muted">Loading…</p></div>

  const negative = data.lowest_balance < 0

  return (
    <div className="view">
      <h2>Cash Flow</h2>
      <p className="muted">
        Projection from a starting balance of <b>{fmt(data.start_balance)}</b> over the
        next ~45 days. {negative ? (
          <span className="warn"> Heads up: balance dips to {fmt(data.lowest_balance)} — you may need to move a bill.</span>
        ) : (
          <span> Lowest projected balance: {fmt(data.lowest_balance)}.</span>
        )}
      </p>

      <table className="data-table">
        <thead>
          <tr><th>Date</th><th>Event</th><th className="num">Amount</th><th className="num">Balance</th></tr>
        </thead>
        <tbody>
          {data.events.map((e, i) => (
            <tr key={i} className={e.alert_type === 'PAY_NOW' ? 'urgency-critical' : ''}>
              <td>{e.date}</td>
              <td>
                {e.kind === 'payday' ? '💵 ' : '🧾 '}
                {e.label}
                {e.alert_type === 'PAY_NOW' && <span className="pill urgency-pill-critical">PAY NOW</span>}
              </td>
              <td className={`num ${e.amount < 0 ? 'neg' : 'pos'}`}>{fmt(e.amount)}</td>
              <td className={`num ${e.balance < 0 ? 'neg' : ''}`}>{fmt(e.balance)}</td>
            </tr>
          ))}
          {data.events.length === 0 && (
            <tr><td colSpan={4} className="muted empty">No upcoming bills or paychecks — add some in Manage.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
