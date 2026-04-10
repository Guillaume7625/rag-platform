'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Citation = {
  document_name: string;
  page: number | null;
  excerpt: string;
};

type Msg = {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  mode_used?: string;
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 60 ? 'bg-emerald-500' : pct >= 30 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-medium text-slate-400">{pct}%</span>
    </div>
  );
}

function Citations({ items }: { items: Citation[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs font-medium text-slate-400 transition-colors hover:text-slate-600"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {items.length} source{items.length > 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-2 animate-slide-up">
          {items.map((c, j) => (
            <div key={j} className="rounded-lg border border-slate-100 bg-slate-50/50 p-2.5">
              <div className="text-xs font-medium text-slate-600">
                [{j + 1}] {c.document_name}
                {c.page ? ` — p.${c.page}` : ''}
              </div>
              <div className="mt-1 text-xs italic text-slate-400 line-clamp-2">{c.excerpt}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        >
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center animate-fade-in">
              <div className="mb-4 rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100 p-4">
                <MessageSquare size={28} className="text-brand-600" />
              </div>
              <p className="text-sm font-medium text-slate-700">Ask anything about your documents</p>
              <p className="mt-1 max-w-xs text-xs text-slate-400">
                Answers are grounded in your uploaded files with cited sources and confidence scores.
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex animate-slide-up ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xl text-sm ${
                  m.role === 'user'
                    ? 'rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-white shadow-sm'
                    : 'rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-slate-900 shadow-sm'
                }`}
              >
                {m.role === 'assistant' ? (
                  <div className="max-w-none [&_h1]:text-base [&_h1]:font-bold [&_h1]:mb-2 [&_h2]:text-sm [&_h2]:font-bold [&_h2]:mb-1 [&_p]:mb-2 [&_p]:last:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:mb-2 [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:mb-2 [&_li]:mb-0.5 [&_strong]:font-semibold [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:rounded [&_code]:text-xs">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && (
                  <Citations items={m.citations} />
                )}
                {m.role === 'assistant' && m.confidence != null && (
                  <div className="mt-2 flex items-center gap-3">
                    <ConfidenceBar value={m.confidence} />
                    <span className="text-[10px] uppercase tracking-wide text-slate-400">{m.mode_used}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start animate-slide-up">
              <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <div className="h-2 w-2 animate-bounce rounded-full bg-slate-300" style={{ animationDelay: '0ms' }} />
                <div className="h-2 w-2 animate-bounce rounded-full bg-slate-300" style={{ animationDelay: '150ms' }} />
                <div className="h-2 w-2 animate-bounce rounded-full bg-slate-300" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
        </div>

        <form onSubmit={onSend} className="mt-4 flex gap-2">
          <input
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm transition-all duration-150 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition-all duration-150 hover:bg-brand-700 hover:shadow-md disabled:opacity-50"
            disabled={loading || !input.trim()}
          >
            <Send size={16} className="transition-transform group-hover:translate-x-0.5" />
          </button>
        </form>
      </div>
    </AppShell>
  );
}
