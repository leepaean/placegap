import type { DiagnosticState, Evidence, Finding, Place, VerificationStatus } from './types'

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
  addEvidence: (input: Partial<Evidence> & Pick<Evidence, 'place_id' | 'title' | 'source_type' | 'excerpt'>) =>
    request<Evidence>('/evidence', { method: 'POST', body: JSON.stringify(input) }),
  addFinding: (input: Partial<Finding> & Pick<Finding, 'place_id' | 'statement' | 'dimension' | 'evidence_ids'>) =>
    request<Finding>('/findings', { method: 'POST', body: JSON.stringify(input) }),
  verifyFinding: (findingId: string, status: VerificationStatus, humanRevision?: string) =>
    request<Finding>(`/findings/${findingId}/verify`, {
      method: 'PATCH',
      body: JSON.stringify({ status, human_revision: humanRevision ?? null }),
    }),
}
