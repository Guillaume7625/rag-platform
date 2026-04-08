export type DocumentState =
  | 'uploaded'
  | 'parsing'
  | 'chunking'
  | 'embedding'
  | 'indexed'
  | 'failed';

export interface DocumentDTO {
  id: string;
  name: string;
  mime_type: string | null;
  size_bytes: number | null;
  state: DocumentState;
  tags: string[];
  allowed_roles: string[];
  created_at: string;
  updated_at: string;
  error: string | null;
}

export interface CitationDTO {
  document_id: string;
  document_name: string;
  page: number | null;
  chunk_id: string;
  excerpt: string;
}

export interface ChatQueryResponseDTO {
  answer: string;
  citations: CitationDTO[];
  confidence: number;
  mode_used: 'standard' | 'deep';
  latency_ms: number;
  conversation_id: string;
  message_id: string;
}
