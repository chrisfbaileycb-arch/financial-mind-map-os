import { useEffect, useState } from 'react'
import { api } from '../api.js'

const JOURNEYS = [
  { id: 'child', icon: '✦', title: 'Welcome a child', prompt: 'Plan for a growing family', target: 5000 },
  { id: 'college', icon: '◈', title: 'Save for college', prompt: 'Build a learning fund', target: 20000 },
  { id: 'home', icon: '⌂', title: 'Buy a first home', prompt: 'Prepare a down payment', target: 30000 },
  { id: 'business', icon: '▣', title: 'Start a business', prompt: 'Create a startup reserve', target: 10000 },
  { id: 'retirement', icon: '◎', title: 'Plan retirement', prompt: 'Set a personal savings target', target: 50000 },
]

const dollars = (value) => new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', maximumFractionDigits: 0,
}).format(Number(value) || 0)

export default function PlanningView({ onNavigate, onRefresh }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(JOURNEYS[2])
  const [target, setTarget] = useState(30000)
  const [monthly, setMonthly] = useState(500)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([api.networth(), api.cashflow(), api.goals(), api.latestReport()])
      .then(([networth, cashflow, goals, report]) => {
        if (active) setData({ networth, cashflow, goals, report })
      })
      .catch((e) => { if (active) setError(e.message) })
    return () => { active = false }
  }, [])

  const select = (journey) => {
    setSelected(journey)
    setTarget(journey.target)
    setSaved('')
  }

  const amount = Number(target)
  const contribution = Number(monthly)
  const valid = Number.isFinite(amount) && amount > 0 && Number.isFinite(contribution) && contribution > 0
  const months = valid ? Math.ceil(amount / contribution) : null
  const taxable = data?.networth?.summary?.by_bucket?.BUCKET_TAXABLE
  const low = data?.cashflow?.lowest_balance
  const pending = (data?.report?.items || []).filter((item) => item.status === 'PENDING').length

  const saveGoal = async () => {
    if (!valid) return
    setSaving(true)
    setError('')
    try {
      await api.createGoal({ label: selected.title, target_amount: amount, monthly_contribution: contribution })
      const goals = await api.goals()
      setData((prev) => ({ ...prev, goals }))
      setSaved('Goal saved to your local financial records. No money was moved.')
      onRefresh?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="planning-view">
      <section className="planning-hero">
        <div className="planning-hero-copy">
          <span className="planning-eyebrow">YOUR MONEY · YOUR NEXT CHAPTER</span>
          <h1>Make room for what matters next.</h1>
          <p>Explore a goal, see the numbers behind it, and keep the next step connected to your financial map.</p>
          <div className="planning-hero-actions">
            <button className="planning-primary" onClick={() => document.getElementById('journeys')?.scrollIntoView({ behavior: 'smooth' })}>Explore life plans</button>
            <button className="planning-secondary" onClick={() => onNavigate('map')}>Open my mind map ↗</button>
          </div>
        </div>
        <div className="planning-companion" aria-label="Friendly financial map companion">
          <span className="planning-orbit orbit-one">$</span><span className="planning-orbit orbit-two">✦</span><span className="planning-orbit orbit-three">%</span>
          <div className="planning-face"><span className="planning-ear left" /><span className="planning-ear right" /><span className="planning-eyes">• &nbsp; •</span><span className="planning-smile">⌣</span></div>
          <p>Let’s look at the whole picture.</p>
        </div>
      </section>

      {error && <div className="planning-error" role="alert">{error}</div>}
      <section className="planning-facts" aria-label="Current financial picture">
        <div><span>Taxable account balance</span><strong>{data ? dollars(taxable) : 'Loading…'}</strong><small>From your current records</small></div>
        <div><span>Lowest projected balance</span><strong>{data ? dollars(low) : 'Loading…'}</strong><small>Within the current cash-flow window</small></div>
        <div><span>Goals in progress</span><strong>{data ? data.goals.length : 'Loading…'}</strong><small>Saved in the finance engine</small></div>
        <div><span>Items to review</span><strong>{data ? pending : 'Loading…'}</strong><small>Nothing acts without your approval</small></div>
      </section>

      <section className="planning-section" id="journeys">
        <span className="planning-eyebrow">PICK A DIRECTION</span>
        <h2>Life changes. Your plan can change with it.</h2>
        <p>These are starting points. Set your own target and monthly contribution below.</p>
        <div className="journey-grid">
          {JOURNEYS.map((journey) => (
            <button key={journey.id} onClick={() => select(journey)} className={`journey-card ${selected.id === journey.id ? 'chosen' : ''}`} aria-pressed={selected.id === journey.id}>
              <span className="journey-icon">{journey.icon}</span><strong>{journey.title}</strong><small>{journey.prompt}</small><span className="journey-arrow">↗</span>
            </button>
          ))}
        </div>
      </section>

      <section className="planning-workspace" aria-label="Goal planning scenario">
        <div className="planning-form">
          <span className="planning-eyebrow">A SIMPLE FIRST SCENARIO</span>
          <h2>{selected.title}</h2>
          <p>Estimate how long it would take to save a target with a fixed monthly contribution. This assumes no growth, interest, inflation, taxes, or withdrawals.</p>
          <label>Goal amount <input type="number" min="1" step="1" value={target} onChange={(e) => setTarget(e.target.value)} /></label>
          <label>Monthly contribution <input type="number" min="1" step="1" value={monthly} onChange={(e) => setMonthly(e.target.value)} /></label>
          <button className="planning-primary" disabled={!valid || saving || !data} onClick={saveGoal}>{saving ? 'Saving…' : 'Save this goal'}</button>
          {saved && <p className="planning-success" role="status">{saved}</p>}
        </div>
        <div className="planning-result">
          <span className="planning-eyebrow">YOUR ESTIMATE</span>
          <strong className="planning-big-number">{months === null ? '—' : `${months} months`}</strong>
          <p>to reach {valid ? dollars(amount) : 'your target'} at {valid ? dollars(contribution) : '—'} per month.</p>
          <div className="planning-note">This contribution is a planning input. It is not subtracted from your cash-flow forecast until you record an actual transfer. Check your projected balance and upcoming bills before committing.</div>
          <button className="planning-secondary" onClick={() => onNavigate('cashflow')}>Review cash flow ↗</button>
        </div>
      </section>
      <p className="planning-disclaimer">Planning estimates are educational and may be wrong. This app does not give personalized investment, tax, or legal advice.</p>
    </main>
  )
}
