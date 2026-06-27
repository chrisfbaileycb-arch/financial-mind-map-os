// The Action Report inbox: every finding requires an explicit decision.

const URGENCY_ORDER = { CRITICAL: 0, HIGH: 1, NORMAL: 2, LOW: 3 }

function StatusPill({ status }) {
  return <span className={`pill status-${status.toLowerCase()}`}>{status}</span>
}

export default function ActionInbox({ report, items, onResolve }) {
  const sorted = [...items].sort(
    (a, b) =>
      (a.status === 'PENDING' ? 0 : 1) - (b.status === 'PENDING' ? 0 : 1) ||
      (URGENCY_ORDER[a.urgency] ?? 9) - (URGENCY_ORDER[b.urgency] ?? 9),
  )

  return (
    <div className="inbox">
      <h2>Action Report</h2>
      {report ? (
        <p className="summary">{report.summary}</p>
      ) : (
        <p className="summary muted">No report yet. Run a sync to generate one.</p>
      )}

      <ul className="items">
        {sorted.map((item) => (
          <li key={item.id} className={`item urgency-${item.urgency.toLowerCase()}`}>
            <div className="item-head">
              <span className="type">{item.item_type.replace(/_/g, ' ')}</span>
              {item.status === 'PENDING' ? (
                <span className={`pill urgency-pill-${item.urgency.toLowerCase()}`}>
                  {item.urgency}
                </span>
              ) : (
                <StatusPill status={item.status} />
              )}
            </div>
            <p className="desc">{item.description}</p>
            {item.status === 'PENDING' && (
              <div className="decision">
                <button className="btn approve" onClick={() => onResolve(item.id, 'APPROVED')}>
                  Approve
                </button>
                <button className="btn deny" onClick={() => onResolve(item.id, 'DENIED')}>
                  Deny
                </button>
                <button className="btn snooze" onClick={() => onResolve(item.id, 'SNOOZED')}>
                  Snooze
                </button>
              </div>
            )}
          </li>
        ))}
        {sorted.length === 0 && <li className="empty muted">Nothing to review. 🎉</li>}
      </ul>
    </div>
  )
}
