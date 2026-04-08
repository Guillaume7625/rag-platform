'use client';

import { useState } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Msg = {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    document_name: string;
    page: number | null;
    excerpt: string;
  }>;
  confidence?: number;
  mode_used?: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const userMsg: Msg = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const res = await api.chatQuery(userMsg.content, conversationId);
      setConversationId(res.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          citations: res.citations,
          confidence: res.confidence,
          mode_used: res.mode_used,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${(err as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto flex h-[calc(100vh-3rem)] max-w-3xl flex-col">
        <h1 className="mb-4 text-2xl font-semibold">Chat</h1>
        <div className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
          {messages.length === 0 && (
            <div className="text-sm text-slate-500">
              Ask anything about your indexed documents.
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
              <div
                className={`inline-block max-w-xl rounded-lg px-4 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-100 text-slate-900'
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                  <div className="mt-2 space-y-1 text-xs text-slate-600">
                    <div className="font-medium">Sources</div>
                    {m.citations.map((c, j) => (
                      <div key={j} className="border-l-2 border-slate-300 pl-2">
                        <div className="font-medium">
                          [{j + 1}] {c.document_name}
                          {c.page ? ` — p.${c.page}` : ''}
                        </div>
                        <div className="italic">{c.excerpt}</div>
                      </div>
                    ))}
                  </div>
                )}
                {m.role === 'assistant' && m.mode_used && (
                  <div className="mt-2 text-[10px] uppercase text-slate-500">
                    mode: {m.mode_used} · confidence: {m.confidence?.toFixed(2)}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="text-sm text-slate-500">Thinking…</div>}
        </div>

        <form onSubmit={onSend} className="mt-4 flex gap-2">
          <input
            className="flex-1 rounded-md border border-slate-300 px-3 py-2"
            placeholder="Ask a question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-50"
            disabled={loading}
          >
            Send
          </button>
        </form>
      </div>
    </AppShell>
  );
}
