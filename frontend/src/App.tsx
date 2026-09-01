import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import {
  DIMENSIONS,
  EVIDENCE_KINDS,
  type DiagnosticState,
  type Dimension,
  type EvidenceKind,
  type FindingProposal,
  type LLMStatus,
  type Place,
  type Reliability,
  type SourcePackPayload,
  type VerificationStatus,
} from './types'
import './styles.css'

const SOURCE_TYPES = ['official', 'statistics', 'academic', 'media', 'operator', 'visitor_review', 'field_observation', 'interview', 'planning_document', 'other']
const RELIABILITIES: Reliability[] = ['UNRATED', 'HIGH', 'MEDIUM', 'LOW']

function App() {
  const [places, setPlaces] = useState<Place[]>([])
  const [placeId, setPlaceId] = useState('')
  const [state, setState] = useState<DiagnosticState | null>(null)
  const [proposals, setProposals] = useState<FindingProposal[]>([])
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const evidenceById = useMemo(
    () => new Map((state?.evidence ?? []).map((item) => [item.id, item])),
    [state],
  )
  const sourceById = useMemo(
    () => new Map((state?.sources ?? []).map((item) => [item.id, item])),
    [state],
  )

  async function refreshPlaces(preferred?: string) {
    const items = await api.listPlaces()
    setPlaces(items)
    const next = preferred ?? placeId ?? items[0]?.id ?? ''
    if (next) setPlaceId(next)
  }

  async function refreshState(id = placeId) {
    if (!id) return setState(null)
    setState(await api.state(id))
  }

  useEffect(() => {
    refreshPlaces().catch((e) => setError(String(e)))
    api.llmStatus().then(setLlmStatus).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    setProposals([])
    setNotice('')
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

  async function draftFromEvidence() {
    if (!state?.evidence.length) return
    await run(async () => {
      const proposed = await api.proposeFindings(state.place.id, state.evidence.map((item) => item.id))
      const existing = new Set(
        state.findings.flatMap((finding) => [finding.statement, finding.original_statement ?? '']).filter(Boolean),
      )
      const fresh = proposed.filter((item) => !existing.has(item.statement))
      setProposals(fresh)
      const usedLLM = fresh.some((item) => item.generated_by.startsWith('llm:'))
      setNotice(
        fresh.length
          ? usedLLM
            ? `Generated ${fresh.length} evidence-bound candidate${fresh.length === 1 ? '' : 's'} with suggested dimensions. Human review is still required.`
            : `Drafted ${fresh.length} safe baseline candidate${fresh.length === 1 ? '' : 's'} from Evidence. Configure an LLM to reduce mechanical review work.`
          : 'No new candidates remain. Existing Findings already cover the current Evidence.',
      )
    })
  }

  const proposalKey = (proposal: FindingProposal) => `${proposal.statement}::${proposal.evidence_ids.join(',')}`

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">PlaceGap · v0.0.3 dev</p>
          <h1>Evidence before advice.</h1>
          <p className="lede">Source → Evidence → Finding. Keep origin, representation, and interpretation separate.</p>
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
      {notice && <div className="notice">{notice}</div>}

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

          <section className="panel source-panel">
            <div className="panel-heading compact-heading">
              <div>
                <p className="eyebrow">01 · Source Library</p>
                <h2>Where did this come from?</h2>
                <p className="section-help">A Source is the whole document, webpage, interview, or observation record. It is not yet Evidence or a Finding.</p>
              </div>
              <span className="count">{state.sources.length}</span>
            </div>
            <div className="toolbar">
              <SourceForm placeId={state.place.id} disabled={busy} onSaved={() => run(() => refreshState())} />
              <SourcePackImport
                disabled={busy}
                onImport={(payload) => run(async () => {
                  const result = await api.importSourcePack(state.place.id, payload)
                  await refreshState()
                  setNotice(`Imported ${result.sources_created} Source${result.sources_created === 1 ? '' : 's'} and ${result.evidence_created} Evidence item${result.evidence_created === 1 ? '' : 's'}.`)
                })}
              />
            </div>
            <div className="source-grid">
              {state.sources.length === 0 && <Empty text="Add a Source manually or import a Source Pack. Existing legacy Evidence can still be used without a Source." />}
              {state.sources.map((source) => (
                <article className="source-card" key={source.id}>
                  <div className="card-meta">
                    <span className="badge">{source.source_type}</span>
                    <span className={`reliability reliability-${source.reliability.toLowerCase()}`}>{source.reliability}</span>
                  </div>
                  <h3>{source.title}</h3>
                  {source.source_name && <p className="source-name">{source.source_name}</p>}
                  {source.author && <p className="muted">{source.author}</p>}
                  {source.url && <a href={source.url} target="_blank" rel="noreferrer">Open source ↗</a>}
                </article>
              ))}
            </div>
          </section>

          <div className="two-column">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">02 · Evidence Board</p>
                  <h2>What does the Source actually support?</h2>
                  <p className="section-help">Evidence is explicitly typed as a quote, datum, summary, or observation so a paraphrase cannot masquerade as source wording.</p>
                </div>
                <span className="count">{state.evidence.length}</span>
              </div>
              <EvidenceForm
                placeId={state.place.id}
                sources={state.sources}
                disabled={busy}
                onSaved={() => run(() => refreshState())}
              />
              <div className="card-stack">
                {state.evidence.length === 0 && <Empty text="Represent a relevant excerpt, datum, summary, or observation before forming a diagnosis." />}
                {state.evidence.map((item) => {
                  const linkedSource = item.source_id ? sourceById.get(item.source_id) : undefined
                  return (
                    <article className="evidence-card" key={item.id}>
                      <div className="card-meta">
                        <div className="badge-row">
                          <span className="badge">{item.kind}</span>
                          <span className="badge">{linkedSource?.source_type ?? item.source_type}</span>
                        </div>
                        <span className={`reliability reliability-${item.reliability.toLowerCase()}`}>{item.reliability}</span>
                      </div>
                      <h3>{item.title}</h3>
                      {linkedSource ? <p className="source-link">From Source: {linkedSource.title}</p> : item.source_name && <p className="source-name">{item.source_name}</p>}
                      <blockquote>{item.excerpt}</blockquote>
                      {(linkedSource?.url ?? item.url) && <a href={linkedSource?.url ?? item.url ?? '#'} target="_blank" rel="noreferrer">Open source ↗</a>}
                    </article>
                  )
                })}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">03 · Finding Review</p>
                  <h2>What can we safely say?</h2>
                  <p className="section-help">Findings must be directly supportable by linked Evidence. Interpretation belongs later in Hypotheses.</p>
                </div>
                <span className="count">{state.findings.length}</span>
              </div>

              <div className="finding-tools">
                <button className="primary-action" disabled={busy || state.evidence.length === 0} onClick={draftFromEvidence}>Generate candidate findings</button>
                <p>
                  {llmStatus?.configured
                    ? `LLM mode: ${llmStatus.model}. It may filter, merge and paraphrase only when the result remains directly supported by linked Evidence.`
                    : 'Safe baseline mode: no LLM configured. Candidates are split from Evidence text and inherit the Evidence dimension when available.'}
                </p>
              </div>

              {proposals.length > 0 && (
                <div className="proposal-stack">
                  <div className="proposal-heading"><strong>Candidate Findings</strong><span>{proposals.length} awaiting placement into review</span></div>
                  {proposals.map((proposal) => (
                    <ProposalCard
                      key={proposalKey(proposal)}
                      proposal={proposal}
                      evidenceTitles={proposal.evidence_ids.map((id) => evidenceById.get(id)?.title ?? 'Unknown evidence')}
                      disabled={busy}
                      onDismiss={() => setProposals((items) => items.filter((item) => proposalKey(item) !== proposalKey(proposal)))}
                      onAdd={(dimension) => run(async () => {
                        await api.addFinding({
                          place_id: state.place.id,
                          statement: proposal.statement,
                          dimension,
                          evidence_ids: proposal.evidence_ids,
                          generated_by: proposal.generated_by,
                        })
                        setProposals((items) => items.filter((item) => proposalKey(item) !== proposalKey(proposal)))
                        await refreshState()
                      })}
                    />
                  ))}
                </div>
              )}

              <ManualFindingForm placeId={state.place.id} evidence={state.evidence} disabled={busy} onSaved={() => run(() => refreshState())} />

              <div className="card-stack">
                {state.findings.length === 0 && proposals.length === 0 && <Empty text="Generate candidates from Evidence, then review only the claims worth keeping." />}
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
        <section className="welcome"><h2>Create or choose a place to begin.</h2><p>No dashboard, no auto-strategy. Start with Sources and Evidence.</p></section>
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

function SourceForm({ placeId, onSaved, disabled }: { placeId: string; onSaved: () => void; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState('official')
  const [sourceName, setSourceName] = useState('')
  const [author, setAuthor] = useState('')
  const [url, setUrl] = useState('')
  const [contentText, setContentText] = useState('')
  const [reliability, setReliability] = useState<Reliability>('UNRATED')

  async function submit(e: FormEvent) {
    e.preventDefault()
    await api.addSource({
      place_id: placeId,
      title: title.trim(),
      source_type: sourceType,
      source_name: sourceName.trim() || null,
      author: author.trim() || null,
      url: url.trim() || null,
      content_text: contentText.trim() || null,
      reliability,
    })
    setTitle(''); setSourceName(''); setAuthor(''); setUrl(''); setContentText(''); setReliability('UNRATED'); setOpen(false); onSaved()
  }

  return <div className="composer inline-composer">
    <button className="secondary" onClick={() => setOpen((v) => !v)}>{open ? 'Close source form' : '+ Add source'}</button>
    {open && <form onSubmit={submit} className="stack-form floating-form wide-form">
      <div className="form-row"><label>Source title<input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Document, webpage, interview, observation…" /></label><label>Type<select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>{SOURCE_TYPES.map((x) => <option key={x}>{x}</option>)}</select></label></div>
      <div className="form-row"><label>Publisher / institution<input value={sourceName} onChange={(e) => setSourceName(e.target.value)} /></label><label>Author<input value={author} onChange={(e) => setAuthor(e.target.value)} /></label></div>
      <label>URL<input value={url} onChange={(e) => setUrl(e.target.value)} /></label>
      <label>Source text <span className="optional">optional for now</span><textarea rows={5} value={contentText} onChange={(e) => setContentText(e.target.value)} placeholder="Paste source text if useful. Evidence will still be represented separately." /></label>
      <label>Reliability<select value={reliability} onChange={(e) => setReliability(e.target.value as Reliability)}>{RELIABILITIES.map((x) => <option key={x}>{x}</option>)}</select></label>
      <button disabled={disabled}>Save source</button>
    </form>}
  </div>
}

function SourcePackImport({ onImport, disabled }: { onImport: (payload: SourcePackPayload) => Promise<void>; disabled: boolean }) {
  async function handleFile(file: File | undefined) {
    if (!file) return
    const text = await file.text()
    const payload = JSON.parse(text) as SourcePackPayload
    if (!Array.isArray(payload.sources) || !Array.isArray(payload.evidence)) throw new Error('Source Pack JSON must contain sources[] and evidence[].')
    await onImport(payload)
  }

  return <label className={`secondary file-button ${disabled ? 'disabled' : ''}`}>
    Import source pack
    <input
      type="file"
      accept="application/json,.json"
      disabled={disabled}
      onChange={(e) => {
        const file = e.target.files?.[0]
        handleFile(file).catch((err) => window.alert(err instanceof Error ? err.message : String(err)))
        e.currentTarget.value = ''
      }}
    />
  </label>
}

function EvidenceForm({ placeId, sources, onSaved, disabled }: { placeId: string; sources: DiagnosticState['sources']; onSaved: () => void; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [sourceId, setSourceId] = useState('')
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState('field_observation')
  const [sourceName, setSourceName] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [kind, setKind] = useState<EvidenceKind>('QUOTE')
  const [reliability, setReliability] = useState<Reliability>('UNRATED')

  async function submit(e: FormEvent) {
    e.preventDefault()
    await api.addEvidence({
      place_id: placeId,
      source_id: sourceId || null,
      title: title.trim(),
      excerpt: excerpt.trim(),
      kind,
      reliability,
      source_type: sourceId ? undefined : sourceType,
      source_name: sourceId ? undefined : (sourceName.trim() || null),
    })
    setSourceId(''); setTitle(''); setSourceName(''); setExcerpt(''); setKind('QUOTE'); setReliability('UNRATED'); setOpen(false); onSaved()
  }

  return <div className="composer">
    <button className="secondary" onClick={() => setOpen((v) => !v)}>{open ? 'Close' : '+ Add evidence'}</button>
    {open && <form onSubmit={submit} className="stack-form">
      <label>Source link<select value={sourceId} onChange={(e) => setSourceId(e.target.value)}><option value="">Standalone evidence / direct observation</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.title}</option>)}</select></label>
      {!sourceId && <div className="form-row"><label>Standalone type<select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>{SOURCE_TYPES.map((x) => <option key={x}>{x}</option>)}</select></label><label>Source name<input value={sourceName} onChange={(e) => setSourceName(e.target.value)} /></label></div>}
      <div className="form-row"><label>Evidence title<input required value={title} onChange={(e) => setTitle(e.target.value)} /></label><label>Representation<select value={kind} onChange={(e) => setKind(e.target.value as EvidenceKind)}>{EVIDENCE_KINDS.map((x) => <option key={x}>{x}</option>)}</select></label></div>
      <label>Evidence text / datum<textarea required rows={5} value={excerpt} onChange={(e) => setExcerpt(e.target.value)} placeholder="QUOTE = source wording; DATUM = structured fact; SUMMARY = explicit paraphrase; OBSERVATION = field observation." /></label>
      <label>Reliability<select value={reliability} onChange={(e) => setReliability(e.target.value as Reliability)}>{RELIABILITIES.map((x) => <option key={x}>{x}</option>)}</select></label>
      <button disabled={disabled}>Save evidence</button>
    </form>}
  </div>
}

function ProposalCard({ proposal, evidenceTitles, onAdd, onDismiss, disabled }: { proposal: FindingProposal; evidenceTitles: string[]; onAdd: (dimension: Dimension) => void; onDismiss: () => void; disabled: boolean }) {
  const [dimension, setDimension] = useState<Dimension>(proposal.dimension)
  const modelLabel = proposal.generated_by.startsWith('llm:') ? proposal.generated_by.slice(4) : 'SAFE BASELINE'
  return <article className="proposal-card">
    <div className="card-meta"><span className="badge">{modelLabel}</span><span>PROPOSED</span></div>
    <p className="proposal-statement">{proposal.statement}</p>
    {proposal.support_note && <p className="source-name">Why this is supportable: {proposal.support_note}</p>}
    <div className="evidence-links">{evidenceTitles.map((title) => <span key={title}>↳ {title}</span>)}</div>
    <div className="proposal-actions">
      <label>Suggested dimension<select value={dimension} onChange={(e) => setDimension(e.target.value as Dimension)}>{DIMENSIONS.map((x) => <option key={x}>{x}</option>)}</select></label>
      <button disabled={disabled} onClick={() => onAdd(dimension)}>Add to review</button>
      <button className="ghost" disabled={disabled} onClick={onDismiss}>Dismiss</button>
    </div>
  </article>
}

function ManualFindingForm({ placeId, evidence, onSaved, disabled }: { placeId: string; evidence: DiagnosticState['evidence']; onSaved: () => void; disabled: boolean }) {
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

  return <div className="composer manual-composer">
    <button className="ghost" disabled={evidence.length === 0} onClick={() => setOpen((v) => !v)}>{open ? 'Close manual entry' : 'Add manual finding'}</button>
    {open && <form onSubmit={submit} className="stack-form">
      <label>Atomic finding<textarea required rows={3} value={statement} onChange={(e) => setStatement(e.target.value)} placeholder="Use this expert override only when a needed Finding was not drafted automatically." /></label>
      <label>Dimension<select value={dimension} onChange={(e) => setDimension(e.target.value as Dimension)}>{DIMENSIONS.map((x) => <option key={x}>{x}</option>)}</select></label>
      <fieldset><legend>Evidence links</legend>{evidence.map((item) => <label className="check" key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, item.id] : selected.filter((id) => id !== item.id))} />{item.title}</label>)}</fieldset>
      <button disabled={disabled || !selected.length}>Save finding</button>
    </form>}
  </div>
}

function FindingCard({ finding, evidenceTitles, onReview, disabled }: { finding: DiagnosticState['findings'][number]; evidenceTitles: string[]; onReview: (status: VerificationStatus, revision?: string) => void; disabled: boolean }) {
  const [editing, setEditing] = useState(false)
  const [revision, setRevision] = useState(finding.statement)

  function reviewButtons() {
    if (finding.verification_status === 'REJECTED') {
      return <div className="actions"><button className="secondary" disabled={disabled} onClick={() => onReview('UNVERIFIED')}>Reopen</button></div>
    }
    return <div className="actions">
      {finding.verification_status !== 'ACCEPTED' && <button disabled={disabled} onClick={() => onReview('ACCEPTED')}>{finding.verification_status === 'EDITED' ? 'Accept revision' : 'Accept'}</button>}
      <button className="secondary" disabled={disabled} onClick={() => { setRevision(finding.statement); setEditing(true) }}>{finding.verification_status === 'EDITED' ? 'Edit again' : 'Edit'}</button>
      <button className="danger" disabled={disabled} onClick={() => onReview('REJECTED')}>Reject</button>
    </div>
  }

  return <article className={`finding-card status-${finding.verification_status.toLowerCase()}`}>
    <div className="card-meta"><span className="badge">{finding.dimension}</span><span>{finding.verification_status}</span></div>
    <h3>{finding.statement}</h3>
    {finding.original_statement && <p className="original">Original: {finding.original_statement}</p>}
    <div className="evidence-links">{evidenceTitles.map((title) => <span key={title}>↳ {title}</span>)}</div>
    {editing ? <div className="edit-box"><textarea rows={4} value={revision} onChange={(e) => setRevision(e.target.value)} /><div className="actions"><button disabled={disabled} onClick={() => { onReview('EDITED', revision); setEditing(false) }}>Save revision</button><button className="ghost" onClick={() => setEditing(false)}>Cancel</button></div></div> : reviewButtons()}
  </article>
}

function Empty({ text }: { text: string }) { return <div className="empty">{text}</div> }

export default App
