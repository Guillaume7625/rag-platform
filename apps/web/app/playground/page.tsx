'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Zap, Clock, FileText, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Result = {
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
};

function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 60 ? 'text-emerald-600' : pct >= 30 ? 'text-amber-600' : 'text-red-500';
  return (
    <div className="text-center">
      <div className={`text-3xl font-bold ${color}`}>{pct}%</div>
      <div className="text-xs text-slate-400">Confiance</div>
    </div>
  );
}

export default function PlaygroundPage() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSources, setShowSources] = useState(true);

  async function onTest(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.chatQuery(query);
      setResult(res);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Playground</h1>
          <p className="mt-1 text-sm text-slate-500">Testez et analysez les réponses du moteur RAG</p>
        </div>

        {/* Query input */}
        <form onSubmit={onTest} className="flex gap-2">
          <input
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            placeholder="Entrez une question de test..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
          >
            {loading ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" /> : <Zap size={16} />}
            Tester
          </button>
        </form>

        {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

        {result && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Response (2/3) */}
            <div className="lg:col-span-2 space-y-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-sm font-medium text-slate-500">Réponse générée</h2>
                <div className="max-w-none text-sm text-slate-800 [&_h1]:text-base [&_h1]:font-bold [&_h1]:mb-2 [&_h2]:text-sm [&_h2]:font-bold [&_h2]:mb-1 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:mb-2 [&_ol]:list-decimal [&_ol]:pl-4 [&_li]:mb-0.5 [&_strong]:font-semibold">
                  <ReactMarkdown>{result.answer}</ReactMarkdown>
                </div>
              </div>

              {/* Sources */}
              <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="flex w-full items-center justify-between px-5 py-3 text-sm font-medium text-slate-700"
                >
                  <span>Sources utilisées ({result.citations.length})</span>
                  {showSources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                {showSources && (
                  <div className="border-t border-slate-100 divide-y divide-slate-100">
                    {result.citations.map((c, i) => (
                      <div key={i} className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <FileText size={14} className="text-slate-400" />
                          <span className="text-sm font-medium text-slate-700">[{i + 1}] {c.document_name}</span>
                          {c.page && <span className="text-xs text-slate-400">p.{c.page}</span>}
                        </div>
                        <p className="mt-1 text-xs italic text-slate-500 line-clamp-3">{c.excerpt}</p>
                      </div>
                    ))}
                    {result.citations.length === 0 && (
                      <div className="px-5 py-6 text-center text-sm text-slate-400">Aucune source trouvée</div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Metrics panel (1/3) */}
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-sm font-medium text-slate-500">Métriques</h2>
                <div className="space-y-6">
                  <ConfidenceGauge value={result.confidence} />
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <Clock size={12} />
                        Latence
                      </div>
                      <span className="text-sm font-medium text-slate-900">{(result.latency_ms / 1000).toFixed(1)}s</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <TrendingUp size={12} />
                        Mode
                      </div>
                      <span className="text-sm font-medium text-slate-900 uppercase">{result.mode_used}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <FileText size={12} />
                        Sources
                      </div>
                      <span className="text-sm font-medium text-slate-900">{result.citations.length}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-sm font-medium text-slate-500">Documents trouvés</h2>
                <div className="space-y-2">
                  {[...new Set(result.citations.map((c) => c.document_name))].map((name) => (
                    <div key={name} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs">
                      <FileText size={12} className="text-brand-600" />
                      <span className="truncate text-slate-700">{name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
