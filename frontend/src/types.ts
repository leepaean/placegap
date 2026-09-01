export type Reliability = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNRATED'
export type EvidenceKind = 'QUOTE' | 'DATUM' | 'SUMMARY' | 'OBSERVATION'
export type VerificationStatus = 'UNVERIFIED' | 'ACCEPTED' | 'EDITED' | 'REJECTED'
export type Dimension =
  | 'RESOURCE'
  | 'MEANING'
  | 'VISIBILITY'
  | 'EXPERIENCE'
  | 'PRODUCT'
  | 'CONVERSION'
  | 'ADVOCACY'
  | 'REGENERATION'

export interface Place {
  id: string
  name: string
  location?: string | null
  place_type?: string | null
  description?: string | null
  diagnostic_scope: string
}

export interface Source {
  id: string
  place_id: string
  title: string
  source_type: string
  source_name?: string | null
  author?: string | null
  published_at?: string | null
  collected_at: string
  url?: string | null
  file_reference?: string | null
  content_text?: string | null
  notes?: string | null
  reliability: Reliability
  tags: string[]
}

export interface Evidence {
  id: string
  place_id: string
  source_id?: string | null
  title: string
  excerpt: string
  kind: EvidenceKind
  reliability: Reliability
  scope?: string | null
  tags: string[]
  source_type: string
  source_name?: string | null
  author?: string | null
  published_at?: string | null
  collected_at: string
  url?: string | null
  file_reference?: string | null
  notes?: string | null
}

export interface Finding {
  id: string
  place_id: string
  statement: string
  dimension: Dimension
  evidence_ids: string[]
  generated_by: string
  verification_status: VerificationStatus
  original_statement?: string | null
  human_revision?: string | null
  created_at: string
}

export interface FindingProposal {
  statement: string
  evidence_ids: string[]
  generated_by: string
}

export interface SourcePackPayload {
  sources: Array<{
    key: string
    title: string
    source_type: string
    source_name?: string | null
    author?: string | null
    published_at?: string | null
    url?: string | null
    file_reference?: string | null
    content_text?: string | null
    notes?: string | null
    reliability?: Reliability
    tags?: string[]
  }>
  evidence: Array<{
    source_key?: string | null
    title: string
    excerpt: string
    kind?: EvidenceKind
    reliability?: Reliability
    scope?: string | null
    tags?: string[]
  }>
}

export interface DiagnosticState {
  place: Place
  sources: Source[]
  evidence: Evidence[]
  findings: Finding[]
  gaps: unknown[]
  hypotheses: unknown[]
  evidence_needs: unknown[]
}

export const EVIDENCE_KINDS: EvidenceKind[] = ['QUOTE', 'DATUM', 'SUMMARY', 'OBSERVATION']

export const DIMENSIONS: Dimension[] = [
  'RESOURCE',
  'MEANING',
  'VISIBILITY',
  'EXPERIENCE',
  'PRODUCT',
  'CONVERSION',
  'ADVOCACY',
  'REGENERATION',
]
