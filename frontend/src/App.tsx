import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { DIMENSIONS, type DiagnosticState, type Dimension, type Place, type Reliability } from './types'
import './styles.css'

const SOURCE_TYPES = ['official', 'statistics', 'academic', 'media', 'operator', 'visitor_review', 'field_observation', 'interview', 'planning_document', 'other']

function App() {
  const [places, setPlaces] = useState<Place[]>([])
  const [placeId, setPlaceId] = useState('')
  const [state, setState] = useState<DiagnosticState | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const evidenceById = useMemo(
    () => new Map((state?.evidence ?? []).map((item) => [item.id, item])),
    [state],
  )

  async function refreshPlaces(preferred?: string) {
    const items = await api.listPlaces()
    setPlaces(items)
    const next = preferred ?? placeId ?? items[0]?.id ?? ''
    if (next) setPlaceId(next)
  }

  async function refreshState(id = placeId) {
    if (!id) {
      setState(null)
      return
    }
    setState(await api.state(id))
  }

  useEffect(() => {
    refreshPlaces().catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (placeId) refreshState(placeId).catch((e) => setError(String(e)))
  }, [placeId])

  async function run(action: () => Promise<void>) {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">PlaceGap · v0.0.1</p>
          <h1>Evidence before advice.</h1>
          <p className="lede">A local workbench for separating what a source says from what we think it means.</p>
        </div>
        <div className="place-switcher">
          <label>Active place</label>
          <select value={placeId} onChange={(e) => setPlaceId(e.target.value)}>
            <option value="">Choose a place…</option>
            {places.map((place) => <option key={place.id} value={place.id}>{place.name}</option>)}
          </select>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <CreatePlace onCreate={(place) => run(async () => {
        await refreshPlaces(place.id)
        await refreshState(place.id)
      })} disabled={busy} />

      {state ? (
        <>
          <section className="scope-card">
            <span>Diagnostic scope</span>
            <strong>{state.place.name}</strong>
            <p>{state.place.diagnostic_scope}</p>
          </section>

          <div className="two-column">
            <section className="panel">
              <div className="panel-heading">
                <div><p className="eyebrow">01 · Evidence Board</p><h2>What do we actually have?</h2></div>
                <span className="count">{state.evidence.length}</span>
              </div>
              <EvidenceForm placeId={state.place.id} disabled={busy} onSaved={() => run(() => refreshState())} />
              <div className="card-stack">
                {state.evidence.length === 0 && <Empty text="Add a source before forming a diagnosis." />}
                {state.evidence.map((item) => (
                  <article className="evidence-card" key={item.id}>
                    <div className="card-meta">
                      <span className="badge">{item.source_type}</span>
                      <span className={`reliability reliability-${item.reliability.toLowerCase()}`}>{item.reliability}</span>
                    </div>
                    <h3>{item.title}</h3>
                    {item.source_name && <p className="source-name">{item.source_name}</p>}
                    <blockquote>{item.excerpt}</blockquote>
                    {item.url && <a href={item.url} target="_blank" rel="noreferrer">Open source ↗</a>}
                  </article>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div><p className="eyebrow">02 · Finding Review</p><h2>What can we safely say?</h2></div>
                <span className="count">{state.findings.length}</span>
              </div>
              <FindingForm placeId={state.place.id} evidence={state.evidence} disabled={busy} onSaved={() => run(() => refreshState())} />
              <div className="card-stack">
                {state.findings.length === 0 && <Empty text="Turn evidence into atomic, reviewable findings." />}
                {state.findings.map((finding) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    evidenceTitles={finding.evidence_ids.map((id) => evidenceById.get(id)?.title ?? 'Unknown evidence')}
                    disabled={busy}
                    onReview={(status, revision) => run(async () => {
                      await api.verifyFinding(finding.id, status, revision)
                      await refreshState()
                    })}
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      ) : (
        <section className="welcome"><h2>Create or choose a place to begin.</h2><p>No dashboard, no auto-strategy. Start with evidence.</p></section>
      )}
    </main>
  )
}

function CreatePlace({ onCreate, disabled }: { onCreate: (place: Place) => void; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [scope, setScope] = useState('')

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim() || !scope.trim()) return
    const place = await api.createPlace({ name: name.trim(), diagnostic_scope: scope.trim() })
    setName(''); setScope(''); setOpen(false); onCreate(place)
  }

  return <section className="create-place">
    <button className="secondary" onClick={() => setOpen((v) => !v)}>{open ? 'Cancel' : '+ New place'}</button>
    {open && <form className="inline-form" onSubmit={submit}>
      <label>Name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Qianfoyan / 千佛岩" /></label>
      <label className="grow">Diagnostic scope<input value={scope} onChange={(e) => setScope(e.target.value)} placeholder="What are we diagnosing, and what is explicitly out of scope?" /></label>
      <button disabled={disabled}>Create</button>
    </form>}
  </section>
}

function EvidenceForm({ placeId, onSaved, disabled }: { placeId: string; onSaved: () => void; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState('official')
  const [sourceName, setSourceName] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [url, setUrl] = useState('')
  const [reliability, setReliability] = useState<Reliability>('UNRATED')

  async function submit(e: FormEvent) {
    e.preventDefault()
    await api.addEvidence({ place_id: placeId, title, source_type: sourceType, source_name: sourceName || null, excerpt, url: url || null, reliability })
    setTitle(''); setSourceName(''); setExcerpt(''); setUrl(''); setReliability('UNRATED'); setOpen(false); onSaved()
  }

  return <div className="composer">
    <button className="secondary" onClick={() => setOpen((v) => !v)}>{open ? 'Close' : '+ Add evidence'}</button>
    {open && <form onSubmit={submit} className="stack-form">
      <div className="form-row"><label>Title<input required value={title} onChange={(e) => setTitle(e.target.value)} /></label><label>Type<select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>{SOURCE_TYPES.map((x) => <option key={x}>{x}</option>)}</select></label></div>
      <label>Source name<input value={sourceName} onChange={(e) => setSourceName(e.target.value)} placeholder="Institution, publication, interviewee…" /></label>
      <label>Exact excerpt / datum<textarea required rows={5} value={excerpt} onChange={(e) => setExcerpt(e.target.value)} /></label>
      <div className="form-row"><label>URL<input value={url} onChange={(e) => setUrl(e.target.value)} /></label><label>Reliability<select value={reliability} onChange={(e) => setReliability(e.target.value as Reliability)}>{['UNRATED','HIGH','MEDIUM','LOW'].map((x) => <option key={x}>{x}</option>)}</select></label></div>
      <button disabled={disabled}>Save evidence</button>
    </form>}
  </div>
}

function FindingForm({ placeId, evidence, onSaved, disabled }: { placeId: string; evidence: DiagnosticState['evidence']; onSaved: () => void; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [statement, setStatement] = useState('')
  const [dimension, setDimension] = useState<Dimension>('RESOURCE')
  const [selected, setSelected] = useState<string[]>([])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!selected.length) return
    await api.addFinding({ place_id: placeId, statement, dimension, evidence_ids: selected, generated_by: 'human' })
    setStatement(''); setSelected([]); setOpen(false); onSaved()
  }

  return <div className="composer">
    <button className="secondary" disabled={evidence.length === 0} onClick={() => setOpen((v) => !v)}>{open ? 'Close' : '+ Add finding'}</button>
    {open && <form onSubmit={submit} className="stack-form">
      <label>Atomic finding<textarea required rows={3} value={statement} onChange={(e) => setStatement(e.target.value)} placeholder="Only state what the linked evidence directly supports." /></label>
      <label>Dimension<select value={dimension} onChange={(e) => setDimension(e.target.value as Dimension)}>{DIMENSIONS.map((x) => <option key={x}>{x}</option>)}</select></label>
      <fieldset><legend>Evidence links</legend>{evidence.map((item) => <label className="check" key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, item.id] : selected.filter((id) => id !== item.id))} />{item.title}</label>)}</fieldset>
      <button disabled={disabled || !selected.length}>Save finding</button>
    </form>}
  </div>
}

function FindingCard({ finding, evidenceTitles, onReview, disabled }: { finding: DiagnosticState['findings'][number]; evidenceTitles: string[]; onReview: (status: 'ACCEPTED' | 'EDITED' | 'REJECTED', revision?: string) => void; disabled: boolean }) {
  const [editing, setEditing] = useState(false)
  const [revision, setRevision] = useState(finding.statement)
  return <article className={`finding-card status-${finding.verification_status.toLowerCase()}`}>
    <div className="card-meta"><span className="badge">{finding.dimension}</span><span>{finding.verification_status}</span></div>
    <h3>{finding.statement}</h3>
    {finding.original_statement && <p className="original">Original: {finding.original_statement}</p>}
    <div className="evidence-links">{evidenceTitles.map((title) => <span key={title}>↳ {title}</span>)}</div>
    {editing ? <div className="edit-box"><textarea rows={4} value={revision} onChange={(e) => setRevision(e.target.value)} /><div className="actions"><button disabled={disabled} onClick={() => { onReview('EDITED', revision); setEditing(false) }}>Save revision</button><button className="ghost" onClick={() => setEditing(false)}>Cancel</button></div></div> : <div className="actions"><button disabled={disabled} onClick={() => onReview('ACCEPTED')}>Accept</button><button className="secondary" disabled={disabled} onClick={() => setEditing(true)}>Edit</button><button className="danger" disabled={disabled} onClick={() => onReview('REJECTED')}>Reject</button></div>}
  </article>
}

function Empty({ text }: { text: string }) { return <div className="empty">{text}</div> }

export default App
