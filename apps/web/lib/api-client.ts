// In production the frontend is served on the same origin as Caddy, which
// proxies /api/* to the FastAPI service. In development we point at the API
// container directly via NEXT_PUBLIC_API_BASE_URL=http://localhost:8000.
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '/api';

export type ApiError = { detail: string };

function authHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = window.localStorage.getItem('rag_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(),
      ...(init.headers || {}),
    },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({ detail: res.statusText }))) as ApiError;
    throw new Error(body.detail || 'request failed');
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string, full_name?: string) =>
    request<{ access_token: string; token_type: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name }),
    }),
  me: () =>
    request<{
      id: string;
      email: string;
      tenant_id: string;
      role: string;
    }>('/auth/me'),
  listDocuments: () =>
    request<{
      items: Array<{
        id: string;
        name: string;
        state: string;
        mime_type: string | null;
        tags: string[];
        created_at: string;
        updated_at: string;
      }>;
      total: number;
    }>('/documents'),
  uploadDocument: async (file: File, tags: string, allowedRoles: string) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('tags', tags);
    fd.append('allowed_roles', allowedRoles);
    const res = await fetch(`${BASE}/documents/upload`, {
      method: 'POST',
      headers: { ...authHeader() },
      body: fd,
    });
    if (!res.ok) throw new Error('upload failed');
    return res.json();
  },
  reindex: (id: string) =>
    request<unknown>(`/documents/${id}/reindex`, { method: 'POST' }),
  deleteDocument: (id: string) =>
    request<unknown>(`/documents/${id}`, { method: 'DELETE' }),
  chatQuery: (query: string, conversation_id?: string) =>
    request<{
      answer: string;
      citations: Array<{
        document_id: string;
        document_name: string;
        page: number | null;
        chunk_id: string;
        excerpt: string;
      }>;
      confidence: number;
      mode_used: string;
      latency_ms: number;
      conversation_id: string;
      message_id: string;
    }>('/chat/query', {
      method: 'POST',
      body: JSON.stringify({ query, conversation_id }),
    }),
  listConversations: () =>
    request<
      Array<{
        id: string;
        title: string | null;
        created_at: string;
      }>
    >('/conversations'),
};
