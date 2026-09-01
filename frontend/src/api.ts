import type {
  DiagnosticState,
  Evidence,
  Finding,
  FindingProposal,
  Place,
  Source,
  SourcePackPayload,
  VerificationStatus,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listPlaces: () => request<Place[]>('/places'),
  createPlace: (input: Pick<Place, 'name' | 'diagnostic_scope'> & Partial<Place>) =>
    request<Place>('/places', { method: 'POST', body: JSON.stringify(input) }),
  state: (placeId: string) => request<DiagnosticState>(`/places/${placeId}/diagnostic-state`),
  addSource: (input: Partial<Source> & Pick<Source, 'place_id' | 'title' | 'source_type'>) =>
    request<Source>('/sources', { method: 'POST', body: JSON.stringify(input) }),
  importSourcePack: (placeId: string, input: SourcePackPayload) =>
    request<{ sources_created: number; evidence_created: number }>(`/places/${placeId}/source-packs/import`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  addEvidence: (input: Partial<Evidence> & Pick<Evidence, 'place_id' | 'title' | 'excerpt'>) =>
    request<Evidence>('/evidence', { method: 'POST', body: JSON.stringify(input) }),
  proposeFindings: (placeId: string, evidenceIds: string[]) =>
    request<FindingProposal[]>(`/places/${placeId}/finding-proposals`, {
      method: 'POST',
      body: JSON.stringify({ evidence_ids: evidenceIds }),
    }),
  addFinding: (input: Partial<Finding> & Pick<Finding, 'place_id' | 'statement' | 'dimension' | 'evidence_ids'>) =>
    request<Finding>('/findings', { method: 'POST', body: JSON.stringify(input) }),
  verifyFinding: (findingId: string, status: VerificationStatus, humanRevision?: string) =>
    request<Finding>(`/findings/${findingId}/verify`, {
      method: 'PATCH',
      body: JSON.stringify({ status, human_revision: humanRevision ?? null }),
    }),
}
