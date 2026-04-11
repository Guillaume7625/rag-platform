'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, MessageSquare, Clock, TrendingUp, Upload, Zap, AlertCircle } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type DashboardData = {
  documents: { total: number; indexed: number; failed: number };
  conversations: { total: number; recent_7d: number };
  messages: { total: number; recent_7d: number };
  performance: { avg_latency_ms: number | null; avg_confidence: number | null };
  recent_conversations: Array<{ id: string; title: string | null; created_at: string | null }>;
};

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: any; label: string; value: string | number; sub?: string; color: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:shadow-md">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
          {sub && <p className="mt-0.5 text-xs text-slate-400">{sub}</p>}
        </div>
        <div className={`rounded-lg p-2.5 ${color}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl border border-slate-200 bg-white" />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-xl border border-slate-200 bg-white" />
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboardStats().then(setData).catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Tableau de bord</h1>
            <p className="mt-1 text-sm text-slate-500">Vue d'ensemble de votre espace</p>
          </div>
          <div className="flex gap-2">
            <Link href="/documents" className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50">
              <Upload size={14} />
              Importer
            </Link>
            <Link href="/chat" className="flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700">
              <MessageSquare size={14} />
              Nouvelle question
            </Link>
          </div>
        </div>

        {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

        {!data ? <DashboardSkeleton /> : (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                icon={FileText}
                label="Documents indexés"
                value={data.documents.indexed}
                sub={`${data.documents.total} au total${data.documents.failed > 0 ? ` · ${data.documents.failed} en erreur` : ''}`}
                color="bg-blue-50 text-blue-600"
              />
              <StatCard
                icon={MessageSquare}
                label="Questions traitées"
                value={data.messages.total}
                sub={`${data.messages.recent_7d} ces 7 derniers jours`}
                color="bg-purple-50 text-purple-600"
              />
              <StatCard
                icon={Clock}
                label="Temps moyen"
                value={data.performance.avg_latency_ms ? `${(data.performance.avg_latency_ms / 1000).toFixed(1)}s` : '-'}
                sub="Latence de réponse"
                color="bg-amber-50 text-amber-600"
              />
              <StatCard
                icon={TrendingUp}
                label="Confiance moyenne"
                value={data.performance.avg_confidence ? `${Math.round(data.performance.avg_confidence * 100)}%` : '-'}
                sub="Score de pertinence"
                color="bg-emerald-50 text-emerald-600"
              />
            </div>

            {/* Recent activity + Quick actions */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {/* Recent conversations */}
              <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-5 py-3">
                  <span className="text-sm font-medium text-slate-700">Conversations récentes</span>
                </div>
                <div className="divide-y divide-slate-100">
                  {data.recent_conversations.length === 0 ? (
                    <div className="px-5 py-8 text-center text-sm text-slate-400">
                      Aucune conversation pour le moment
                    </div>
                  ) : (
                    data.recent_conversations.map((c) => (
                      <Link key={c.id} href="/chat" className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-slate-50">
                        <MessageSquare size={14} className="shrink-0 text-slate-400" />
                        <span className="truncate text-sm text-slate-700">{c.title || 'Sans titre'}</span>
                        <span className="ml-auto shrink-0 text-xs text-slate-400">
                          {c.created_at ? new Date(c.created_at).toLocaleDateString('fr-FR') : ''}
                        </span>
                      </Link>
                    ))
                  )}
                </div>
              </div>

              {/* Quick actions */}
              <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-100 px-5 py-3">
                  <span className="text-sm font-medium text-slate-700">Actions rapides</span>
                </div>
                <div className="grid grid-cols-2 gap-3 p-5">
                  <Link href="/documents" className="flex flex-col items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-md">
                    <Upload size={20} className="text-blue-600" />
                    <span className="text-xs font-medium text-slate-700">Importer un PDF</span>
                  </Link>
                  <Link href="/chat" className="flex flex-col items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-md">
                    <MessageSquare size={20} className="text-purple-600" />
                    <span className="text-xs font-medium text-slate-700">Poser une question</span>
                  </Link>
                  <Link href="/playground" className="flex flex-col items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-md">
                    <Zap size={20} className="text-amber-600" />
                    <span className="text-xs font-medium text-slate-700">Playground</span>
                  </Link>
                  <Link href="/analytics" className="flex flex-col items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-4 text-center transition-all hover:-translate-y-0.5 hover:shadow-md">
                    <TrendingUp size={20} className="text-emerald-600" />
                    <span className="text-xs font-medium text-slate-700">Voir les stats</span>
                  </Link>
                </div>
              </div>
            </div>

            {/* Documents failed alert */}
            {data.documents.failed > 0 && (
              <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-5 py-3">
                <AlertCircle size={16} className="text-amber-600" />
                <span className="text-sm text-amber-700">
                  {data.documents.failed} document{data.documents.failed > 1 ? 's' : ''} en erreur.{' '}
                  <Link href="/documents" className="font-medium underline">Voir les détails</Link>
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
