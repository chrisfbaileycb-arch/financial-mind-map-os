import { useMemo, useState } from 'react'
import { api } from '../api.js'

// Split a CSV header line into column names (handles simple quoted fields).
function parseHeader(text) {
  const firstLine = text.split(/\r?\n/)[0] || ''
  const cols = []
  let cur = ''
  let inQuotes = false
  for (const ch of firstLine) {
    if (ch === '"') inQuotes = !inQuotes
    else if (ch === ',' && !inQuotes) {
      cols.push(cur.trim())
      cur = ''
    } else cur += ch
  }
  cols.push(cur.trim())
  return cols.filter(Boolean)
}

function guess(columns, candidates) {
  const lower = columns.map((c) => c.toLowerCase())
  for (const cand of candidates) {
    const idx = lower.findIndex((c) => c.includes(cand))
    if (idx >= 0) return columns[idx]
  }
  return ''
}

function ColSelect({ label, value, onChange, columns, optional }) {
  return (
    <label className="field">
      <span>{label}{optional ? ' (optional)' : ''}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">—</option>
        {columns.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
    </label>
  )
}

export default function ImportPanel({ onClose, onImported }) {
  const [csvText, setCsvText] = useState('')
  const [fileName, setFileName] = useState('')
  const [accountId, setAccountId] = useState('')
  const [mode, setMode] = useState('single') // 'single' | 'split'
  const [map, setMap] = useState({
    date: '', amount: '', debit: '', credit: '', description: '', merchant: '',
  })
  const [flipSign, setFlipSign] = useState(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const columns = useMemo(() => parseHeader(csvText), [csvText])

  const onFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setFileName(file.name)
    setCsvText(text)
    const cols = parseHeader(text)
    setMap({
      date: guess(cols, ['date', 'posted']),
      amount: guess(cols, ['amount']),
      debit: guess(cols, ['debit', 'withdrawal']),
      credit: guess(cols, ['credit', 'deposit']),
      description: guess(cols, ['description', 'memo', 'name', 'detail']),
      merchant: guess(cols, ['merchant', 'payee']),
    })
    setResult(null)
    setError(null)
  }

  const canImport =
    accountId && map.date && (mode === 'single' ? map.amount : map.debit || map.credit)

  const submit = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const mapping = {
        date: map.date,
        description: map.description || null,
        merchant: map.merchant || null,
        flip_sign: flipSign,
      }
      if (mode === 'single') mapping.amount = map.amount
      else {
        mapping.debit = map.debit || null
        mapping.credit = map.credit || null
      }
      const res = await api.importCsv({ account_id: accountId, csv_text: csvText, mapping })
      setResult(res)
      onImported?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Import transactions (CSV)</h2>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>

        <label className="field">
          <span>Account name</span>
          <input
            type="text"
            placeholder="e.g. Chase Checking"
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
          />
        </label>

        <label className="field">
          <span>CSV file</span>
          <input type="file" accept=".csv,text/csv" onChange={onFile} />
        </label>
        {fileName && <p className="muted small">{fileName} — {columns.length} columns</p>}

        {columns.length > 0 && (
          <>
            <div className="mode-toggle">
              <label>
                <input
                  type="radio"
                  checked={mode === 'single'}
                  onChange={() => setMode('single')}
                />
                Single amount column
              </label>
              <label>
                <input
                  type="radio"
                  checked={mode === 'split'}
                  onChange={() => setMode('split')}
                />
                Separate debit / credit
              </label>
            </div>

            <div className="grid">
              <ColSelect label="Date" value={map.date} columns={columns}
                onChange={(v) => setMap({ ...map, date: v })} />
              {mode === 'single' ? (
                <ColSelect label="Amount" value={map.amount} columns={columns}
                  onChange={(v) => setMap({ ...map, amount: v })} />
              ) : (
                <>
                  <ColSelect label="Debit" value={map.debit} columns={columns} optional
                    onChange={(v) => setMap({ ...map, debit: v })} />
                  <ColSelect label="Credit" value={map.credit} columns={columns} optional
                    onChange={(v) => setMap({ ...map, credit: v })} />
                </>
              )}
              <ColSelect label="Description" value={map.description} columns={columns} optional
                onChange={(v) => setMap({ ...map, description: v })} />
              <ColSelect label="Merchant" value={map.merchant} columns={columns} optional
                onChange={(v) => setMap({ ...map, merchant: v })} />
            </div>

            {mode === 'single' && (
              <label className="checkbox">
                <input type="checkbox" checked={flipSign}
                  onChange={(e) => setFlipSign(e.target.checked)} />
                Flip sign (my export uses positive numbers for spending)
              </label>
            )}
          </>
        )}

        {error && <div className="error-banner">{error}</div>}
        {result && (
          <div className="import-result">
            <p>✓ Imported <b>{result.imported}</b> transactions,
              detected <b>{result.detected}</b> subscription(s).</p>
            {result.skipped > 0 && (
              <details>
                <summary>{result.skipped} row(s) skipped</summary>
                <ul>{result.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </details>
            )}
          </div>
        )}

        <div className="modal-foot">
          <button className="btn ghost" onClick={onClose}>Close</button>
          <button className="btn primary" disabled={!canImport || busy} onClick={submit}>
            {busy ? 'Importing…' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  )
}
