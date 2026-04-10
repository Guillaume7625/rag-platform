'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, MessageSquare } from 'lucide-react';
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
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

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
        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4"
        >
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-3 rounded-full bg-brand-50 p-3">
                <MessageSquare size={24} className="text-brand-600" />
              </div>
              <p className="text-sm font-medium text-slate-700">Ask anything about your documents</p>
              <p className="mt-1 text-xs text-slate-400">
                Answers are grounded in your uploaded files with cited sources.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? 'flex justify-end' : ''}>
              <div
                className={`max-w-xl rounded-lg px-4 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-50 text-slate-900 border border-slate-200'
                }`}
              >
                {m.role === 'assistant' ? (
                  <div className="max-w-none [&_h1]:text-base [&_h1]:font-bold [&_h1]:mb-2 [&_h2]:text-sm [&_h2]:font-bold [&_h2]:mb-1 [&_p]:mb-2 [&_p]:last:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:mb-2 [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:mb-2 [&_li]:mb-0.5 [&_strong]:font-semibold [&_code]:bg-slate-200 [&_code]:px-1 [&_code]:rounded [&_code]:text-xs">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                  <div className="mt-3 space-y-1.5 border-t border-slate-200 pt-2 text-xs text-slate-600">
                    <div className="font-medium text-slate-500">Sources</div>
                    {m.citations.map((c, j) => (
                      <div key={j} className="rounded-md bg-white p-2 border border-slate-100">
                        <div className="font-medium text-slate-700">
                          [{j + 1}] {c.document_name}
                          {c.page ? ` — p.${c.page}` : ''}
                        </div>
                        <div className="mt-0.5 italic text-slate-500 line-clamp-2">{c.excerpt}</div>
                      </div>
                    ))}
                  </div>
                )}
                {m.role === 'assistant' && m.mode_used && (
                  <div className="mt-2 text-[10px] uppercase tracking-wide text-slate-400">
                    {m.mode_used} · confidence {(m.confidence! * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-1 px-4 py-2 text-sm text-slate-400">
              <span className="animate-pulse">Thinking</span>
              <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '0.3s' }}>.</span>
            </div>
          )}
        </div>

        <form onSubmit={onSend} className="mt-4 flex gap-2">
          <input
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 disabled:opacity-50"
            disabled={loading || !input.trim()}
          >
            <Send size={16} />
            Send
          </button>
        </form>
      </div>
    </AppShell>
  );
}
