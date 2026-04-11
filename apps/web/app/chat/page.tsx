'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Plus, History, Search, BookOpen, PenTool } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Citation = { document_name: string; page: number | null; excerpt: string };
type Msg = {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  mode_used?: string;
  message_id?: string;
  feedback?: 1 | -1 | null;
};
type ConvSummary = { id: string; title: string | null; created_at: string };

const SUGGESTIONS = [
  'Quels sont les principaux sujets de mes documents ?',
  'Fais une analyse comparative des documents',
  'Quels sont les points clés à retenir ?',
];

const LOADING_STEPS = [
  { icon: Search, label: 'Recherche dans les documents...', delay: 0 },
  { icon: BookOpen, label: 'Analyse des passages pertinents...', delay: 2000 },
  { icon: PenTool, label: 'Rédaction de la réponse...', delay: 5000 },
];

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 overflow-hidden rounded-full bg-stone-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-stone-400">{pct}%</span>
    </div>
  );
}

function Citations({ items }: { items: Citation[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 border-t border-stone-100 pt-2">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600">
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {items.length} source{items.length > 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {items.map((c, j) => (
            <div key={j} className="rounded-md bg-stone-50 p-2 text-xs">
              <span className="font-medium text-stone-600">[{j + 1}] {c.document_name}{c.page ? ` \u2014 p.${c.page}` : ''}</span>
              <p className="mt-0.5 italic text-stone-400 line-clamp-2">{c.excerpt}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FeedbackButtons({ messageId, initial }: { messageId?: string; initial?: 1 | -1 | null }) {
  const [value, setValue] = useState<1 | -1 | null>(initial ?? null);

  async function send(v: 1 | -1) {
    if (!messageId) return;
    const newVal = value === v ? null : v;
    setValue(newVal);
    try {
      await api.sendFeedback(messageId, newVal ?? 0);
    } catch { /* ignore */ }
  }

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => send(1)}
        className={`rounded p-1 transition-colors ${value === 1 ? 'bg-emerald-100 text-emerald-600' : 'text-stone-300 hover:text-stone-500'}`}
      >
        <ThumbsUp size={12} />
      </button>
      <button
        onClick={() => send(-1)}
        className={`rounded p-1 transition-colors ${value === -1 ? 'bg-red-100 text-red-500' : 'text-stone-300 hover:text-stone-500'}`}
      >
        <ThumbsDown size={12} />
      </button>
    </div>
  );
}

function LoadingSteps() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = LOADING_STEPS.map((s, i) => {
      if (i === 0) return null;
      return setTimeout(() => setStep(i), s.delay);
    });
    return () => timers.forEach((t) => t && clearTimeout(t));
  }, []);

  return (
    <div className="space-y-2 rounded-lg bg-stone-50 px-4 py-3">
      {LOADING_STEPS.map((s, i) => {
        const Icon = s.icon;
        const active = i === step;
        const done = i < step;
        return (
          <div key={i} className={`flex items-center gap-2 text-xs transition-opacity ${i > step ? 'opacity-30' : ''}`}>
            {done ? (
              <span className="text-emerald-500">\u2713</span>
            ) : active ? (
              <Icon size={12} className="animate-pulse text-blue-500" />
            ) : (
              <Icon size={12} className="text-stone-300" />
            )}
            <span className={active ? 'text-stone-700 font-medium' : done ? 'text-stone-500' : 'text-stone-400'}>{s.label}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [conversations, setConversations] = useState<ConvSummary[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.listConversations().then(setConversations).catch(() => {}); }, []);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }); }, [messages, loading]);

  function newConversation() { setMessages([]); setConversationId(undefined); }

  async function loadConversation(id: string) {
    setShowHistory(false);
    setConversationId(id);
    try {
      const conv = await api.getConversation(id);
      setMessages(conv.messages.map((m) => ({
        role: m.role,
        content: m.content,
        citations: m.citations,
        confidence: m.confidence ?? undefined,
        mode_used: m.mode_used ?? undefined,
        message_id: m.id,
        feedback: m.feedback as 1 | -1 | null,
      })));
    } catch {
      setMessages([]);
    }
  }

  async function onSend(q?: string) {
    const query = q || input.trim();
    if (!query) return;
    const userMsg: Msg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Add placeholder assistant message for streaming.
    const placeholderIdx = messages.length + 1;
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      let streamedText = '';
      let meta: any = null;
      let messageId: string | undefined;

      for await (const event of api.chatStream(query, conversationId)) {
        if (event.type === 'meta') {
          meta = event;
          setConversationId(event.conversation_id);
        } else if (event.type === 'token') {
          streamedText += event.text;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: streamedText,
              citations: meta?.citations,
              confidence: meta?.confidence,
              mode_used: meta?.mode,
            };
            return updated;
          });
        } else if (event.type === 'done') {
          messageId = event.message_id;
        } else if (event.type === 'error') {
          streamedText += `\n\nErreur : ${event.text}`;
        }
      }

      // Finalize message with message_id for feedback.
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: streamedText,
          message_id: messageId,
          citations: meta?.citations,
          confidence: meta?.confidence,
          mode_used: meta?.mode,
        };
        return updated;
      });

      api.listConversations().then(setConversations).catch(() => {});
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Erreur : ${(err as Error).message}`,
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto flex h-[calc(100vh-3rem)] max-w-3xl flex-col">
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <button onClick={() => setShowHistory(!showHistory)} className="flex items-center gap-1.5 rounded-md border border-stone-200 px-2.5 py-1 text-xs text-stone-500 hover:bg-stone-50">
            <History size={12} /> Historique ({conversations.length})
          </button>
          <button onClick={newConversation} className="flex items-center gap-1.5 rounded-md bg-blue-600 px-2.5 py-1 text-xs text-white hover:bg-blue-700">
            <Plus size={12} /> Nouvelle conversation
          </button>
        </div>

        {showHistory && conversations.length > 0 && (
          <div className="mb-3 max-h-40 overflow-y-auto rounded-lg border border-stone-200 bg-white p-1.5">
            {conversations.map((c) => (
              <button key={c.id} onClick={() => loadConversation(c.id)}
                className="flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-xs hover:bg-stone-50">
                <span className="truncate text-stone-600">{c.title || 'Sans titre'}</span>
                <span className="shrink-0 text-stone-400 ml-2">{new Date(c.created_at).toLocaleDateString('fr-FR')}</span>
              </button>
            ))}
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-stone-200/60 bg-white p-4">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="text-4xl mb-3">{'\u{1F4AC}'}</div>
              <p className="text-sm font-medium text-stone-700">Posez une question sur vos documents</p>
              <p className="mt-1 text-xs text-stone-400 max-w-xs">Les réponses sont fondées sur vos fichiers avec sources citées.</p>

              {/* Suggestions */}
              <div className="mt-6 space-y-2 w-full max-w-sm">
                <p className="text-[10px] uppercase tracking-wide text-stone-400">Suggestions</p>
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => onSend(s)}
                    className="w-full rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-left text-xs text-stone-600 hover:bg-stone-100 transition-colors">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xl text-sm ${m.role === 'user'
                ? 'rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2 text-white'
                : 'rounded-2xl rounded-bl-sm border border-stone-200/60 bg-white px-4 py-3 text-stone-800'
              }`}>
                {m.role === 'assistant' ? (
                  <div className="max-w-none [&_h2]:text-sm [&_h2]:font-bold [&_h2]:mt-3 [&_h2]:mb-1 [&_h3]:text-xs [&_h3]:font-bold [&_h3]:mt-2 [&_h3]:mb-1 [&_p]:mb-2 [&_p]:last:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:mb-2 [&_ol]:list-decimal [&_ol]:pl-4 [&_li]:mb-0.5 [&_strong]:font-semibold [&_hr]:my-3 [&_hr]:border-stone-100">
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
                {m.role === 'assistant' && m.citations && m.citations.length > 0 && <Citations items={m.citations} />}
                {m.role === 'assistant' && (
                  <div className="mt-2 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {m.confidence != null && <ConfidenceBar value={m.confidence} />}
                      {m.mode_used && <span className="text-[10px] text-stone-400">{m.mode_used}</span>}
                    </div>
                    <FeedbackButtons messageId={m.message_id} initial={m.feedback} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && <LoadingSteps />}
        </div>

        {/* Input */}
        <form onSubmit={(e) => { e.preventDefault(); onSend(); }} className="mt-3 flex gap-2">
          <input
            className="flex-1 rounded-lg border border-stone-200 bg-white px-3 py-2.5 text-sm placeholder:text-stone-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Posez votre question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2.5 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors">
            <Send size={16} />
          </button>
        </form>
      </div>
    </AppShell>
  );
}
