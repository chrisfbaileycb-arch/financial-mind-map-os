import { useEffect, useState } from 'react'
import { api } from '../api.js'

const BUCKETS = ['', 'BUCKET_TAXABLE', 'BUCKET_TAX', 'BUCKET_FREE']

export default function ManageView() {
  const [accounts, setAccounts] = useState([])
  const [bills, setBills] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)

  const reload = async () => {
    try {
      const [a, b, m] = await Promise.all([api.accounts(), api.bills(), api.members()])
      setAccounts(a)
      setBills(b.filter((x) => x.status === 'ACTIVE'))
      setMembers(m)
    } catch (e) {
      setError(e.message)
    }
  }
  useEffect(() => { reload() }, [])

  const wrap = (fn) => async (...args) => {
    try { await fn(...args); await reload() } catch (e) { setError(e.message) }
  }

  return (
    <div className="view">
      <h2>Manage</h2>
      {error && <div className="error-banner">{error}</div>}

      <Section title="Members">
        <ul className="mini-list">
          {members.map((m) => (
            <li key={m.member_hash}>
              {m.role || 'member'} · baseline ${m.baseline_monthly}
              {m.spending_limit ? ` · limit $${m.spending_limit}` : ''}
            </li>
          ))}
        </ul>
        <MemberForm onAdd={wrap(api.createMember)} />
      </Section>

      <Section title="Accounts">
        <ul className="mini-list">
          {accounts.map((a) => (
            <li key={a.account_hash}>
              <b>{a.name}</b> · {a.bucket_type || 'no bucket'} ·
              <input
                className="cat-input inline-num"
                type="number"
                defaultValue={a.balance}
                onBlur={(e) =>
                  wrap(api.updateAccount)(a.account_hash, { balance: Number(e.target.value) })
                }
              />
            </li>
          ))}
        </ul>
        <AccountForm onAdd={wrap(api.createAccount)} />
      </Section>

      <Section title="Bills">
        <ul className="mini-list">
          {bills.map((b) => (
            <li key={b.id}>
              <b>{b.label}</b> · $
              <input className="cat-input inline-num" type="number" defaultValue={b.amount}
                onBlur={(e) => wrap(api.updateBill)(b.id, { amount: Number(e.target.value) })} />
              · due day
              <input className="cat-input inline-num small-num" type="number" defaultValue={b.due_day}
                onBlur={(e) => wrap(api.updateBill)(b.id, { due_day: Number(e.target.value) })} />
              {b.auto_pay ? ' · auto-pay' : ''}
              <button className="btn ghost small" onClick={() => wrap(api.deleteBill)(b.id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
        <BillForm onAdd={wrap(api.createBill)} />
      </Section>

      <Section title="Paycheck schedule">
        <ScheduleForm onAdd={wrap(api.createSchedule)} />
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="manage-section">
      <h3>{title}</h3>
      {children}
    </section>
  )
}

function useForm(initial) {
  const [v, setV] = useState(initial)
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value })
  const reset = () => setV(initial)
  return [v, set, reset, setV]
}

function MemberForm({ onAdd }) {
  const [v, set, reset] = useForm({ member_id: '', role: '', baseline_monthly: '', spending_limit: '' })
  return (
    <form className="add-form" onSubmit={(e) => {
      e.preventDefault()
      onAdd({
        member_id: v.member_id,
        role: v.role || null,
        baseline_monthly: Number(v.baseline_monthly) || 0,
        spending_limit: v.spending_limit ? Number(v.spending_limit) : null,
      }).then(reset)
    }}>
      <input placeholder="name/email" value={v.member_id} onChange={set('member_id')} required />
      <input placeholder="role" value={v.role} onChange={set('role')} />
      <input placeholder="baseline $/mo" type="number" value={v.baseline_monthly} onChange={set('baseline_monthly')} />
      <input placeholder="limit $/mo" type="number" value={v.spending_limit} onChange={set('spending_limit')} />
      <button className="btn primary small" type="submit">Add</button>
    </form>
  )
}

function AccountForm({ onAdd }) {
  const [v, set, reset] = useForm({ account_id: '', name: '', bucket_type: '', balance: '', member_id: '' })
  return (
    <form className="add-form" onSubmit={(e) => {
      e.preventDefault()
      onAdd({
        account_id: v.account_id,
        name: v.name,
        bucket_type: v.bucket_type || null,
        balance: Number(v.balance) || 0,
        member_id: v.member_id || null,
      }).then(reset)
    }}>
      <input placeholder="account id" value={v.account_id} onChange={set('account_id')} required />
      <input placeholder="name" value={v.name} onChange={set('name')} required />
      <select value={v.bucket_type} onChange={set('bucket_type')}>
        {BUCKETS.map((b) => <option key={b} value={b}>{b || 'bucket…'}</option>)}
      </select>
      <input placeholder="balance" type="number" value={v.balance} onChange={set('balance')} />
      <input placeholder="owner id (optional)" value={v.member_id} onChange={set('member_id')} />
      <button className="btn primary small" type="submit">Add</button>
    </form>
  )
}

function BillForm({ onAdd }) {
  const [v, set, reset] = useForm({ merchant: '', label: '', amount: '', due_day: '', late_fee: '', category: '', auto_pay: false })
  return (
    <form className="add-form" onSubmit={(e) => {
      e.preventDefault()
      onAdd({
        merchant: v.merchant, label: v.label, amount: Number(v.amount),
        due_day: Number(v.due_day), late_fee: Number(v.late_fee) || 0,
        category: v.category || null, auto_pay: v.auto_pay,
      }).then(reset)
    }}>
      <input placeholder="merchant" value={v.merchant} onChange={set('merchant')} required />
      <input placeholder="label" value={v.label} onChange={set('label')} required />
      <input placeholder="amount" type="number" value={v.amount} onChange={set('amount')} required />
      <input placeholder="due day" type="number" value={v.due_day} onChange={set('due_day')} required />
      <input placeholder="late fee" type="number" value={v.late_fee} onChange={set('late_fee')} />
      <input placeholder="category" value={v.category} onChange={set('category')} />
      <button className="btn primary small" type="submit">Add</button>
    </form>
  )
}

function ScheduleForm({ onAdd }) {
  const [v, set, reset] = useForm({ member_id: '', pay_day_1: '', pay_day_2: '', pay_amount: '' })
  return (
    <form className="add-form" onSubmit={(e) => {
      e.preventDefault()
      onAdd({
        member_id: v.member_id,
        pay_day_1: Number(v.pay_day_1),
        pay_day_2: v.pay_day_2 ? Number(v.pay_day_2) : null,
        pay_amount: v.pay_amount ? Number(v.pay_amount) : null,
      }).then(reset)
    }}>
      <input placeholder="member id" value={v.member_id} onChange={set('member_id')} required />
      <input placeholder="pay day 1" type="number" value={v.pay_day_1} onChange={set('pay_day_1')} required />
      <input placeholder="pay day 2" type="number" value={v.pay_day_2} onChange={set('pay_day_2')} />
      <input placeholder="amount" type="number" value={v.pay_amount} onChange={set('pay_amount')} />
      <button className="btn primary small" type="submit">Add</button>
    </form>
  )
}
