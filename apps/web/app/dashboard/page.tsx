'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type DashboardData = {
  documents: { total: number; indexed: number; failed: number };
  conversations: { total: number; recent_7d: number };
  messages: { total: number; recent_7d: number };
  performance: { avg_latency_ms: number | null; avg_confidence: number | null };
  recent_conversations: Array<{ id: string; title: string | null; created_at: string | null }>;
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboardStats().then(setData).catch((e) => setError(e.message));
  }, []);

  if (!data && !error) {
    return (
      <AppShell>
        <div className="space-y-6 animate-pulse">
          <div className="h-8 w-48 rounded bg-stone-100" />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-24 rounded-lg bg-stone-100" />)}
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Title */}
        <div>
          <h1 className="text-3xl font-bold text-stone-900">{'\u{1F3E0}'} Tableau de bord</h1>
          <p className="mt-1 text-stone-500">Vue d{"'"}ensemble de votre espace de travail</p>
        </div>

        {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 border border-red-100">{error}</div>}

        {data && (
          <>
            {/* KPI blocks - Notion style */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {[
                { emoji: '\u{1F4C4}', label: 'Documents', value: data.documents.indexed, sub: `${data.documents.total} au total` },
                { emoji: '\u{1F4AC}', label: 'Questions', value: data.messages.total, sub: `${data.messages.recent_7d} cette semaine` },
                { emoji: '\u23F1\uFE0F', label: 'Latence', value: data.performance.avg_latency_ms ? `${(data.performance.avg_latency_ms / 1000).toFixed(1)}s` : '-', sub: 'temps moyen' },
                { emoji: '\u{1F3AF}', label: 'Confiance', value: data.performance.avg_confidence ? `${Math.round(data.performance.avg_confidence * 100)}%` : '-', sub: 'score moyen' },
              ].map((kpi) => (
                <div key={kpi.label} className="rounded-lg border border-stone-200/80 bg-white p-4 hover:bg-stone-50 transition-colors">
                  <div className="text-lg mb-1">{kpi.emoji}</div>
                  <div className="text-2xl font-bold text-stone-900">{kpi.value}</div>
                  <div className="text-xs text-stone-500 mt-0.5">{kpi.label} · {kpi.sub}</div>
                </div>
              ))}
            </div>

            {/* Two columns */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Recent conversations */}
              <div>
                <h2 className="text-sm font-medium text-stone-500 mb-3">{'\u{1F4AC}'} Conversations récentes</h2>
                <div className="space-y-1">
                  {data.recent_conversations.length === 0 ? (
                    <p className="text-sm text-stone-400 py-4">Aucune conversation</p>
                  ) : (
                    data.recent_conversations.map((c) => (
                      <Link
                        key={c.id}
                        href="/chat"
                        className="flex items-center justify-between rounded-md px-3 py-2 text-sm text-stone-700 hover:bg-stone-100 transition-colors"
                      >
                        <span className="truncate">{c.title || 'Sans titre'}</span>
                        <span className="shrink-0 text-xs text-stone-400 ml-3">
                          {c.created_at ? new Date(c.created_at).toLocaleDateString('fr-FR') : ''}
                        </span>
                      </Link>
                    ))
                  )}
                </div>
              </div>

              {/* Quick actions */}
              <div>
                <h2 className="text-sm font-medium text-stone-500 mb-3">{'\u26A1'} Actions rapides</h2>
                <div className="space-y-1">
                  {[
                    { href: '/documents', emoji: '\u{1F4E4}', label: 'Importer un document' },
                    { href: '/chat', emoji: '\u{1F4AC}', label: 'Poser une question' },
                    { href: '/playground', emoji: '\u26A1', label: 'Tester le moteur' },
                    { href: '/analytics', emoji: '\u{1F4CA}', label: 'Voir les statistiques' },
                  ].map((a) => (
                    <Link
                      key={a.href}
                      href={a.href}
                      className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-stone-700 hover:bg-stone-100 transition-colors"
                    >
                      <span className="text-base">{a.emoji}</span>
                      {a.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>

            {/* Failed docs alert */}
            {data.documents.failed > 0 && (
              <div className="rounded-lg bg-amber-50 border border-amber-200/60 px-4 py-3 text-sm text-amber-800">
                {'\u26A0\uFE0F'} {data.documents.failed} document{data.documents.failed > 1 ? 's' : ''} en erreur —{' '}
                <Link href="/documents" className="underline">voir les détails</Link>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
