'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Clock, TrendingUp, FileText, MessageSquare, Zap } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Stats = {
  documents: { total: number; indexed: number; failed: number };
  conversations: { total: number; recent_7d: number };
  messages: { total: number; recent_7d: number };
  performance: { avg_latency_ms: number | null; avg_confidence: number | null };
};

function MetricBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-900">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboardStats().then(setStats).catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Analytics</h1>
          <p className="mt-1 text-sm text-slate-500">Usage, qualité et performance</p>
        </div>

        {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

        {!stats ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-40 animate-pulse rounded-xl border border-slate-200 bg-white" />
            ))}
          </div>
        ) : (
          <>
            {/* Usage section */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <div className="rounded-lg bg-blue-50 p-2"><FileText size={16} className="text-blue-600" /></div>
                  <span className="text-sm font-medium text-slate-700">Documents</span>
                </div>
                <div className="space-y-3">
                  <MetricBar label="Indexés" value={stats.documents.indexed} max={stats.documents.total || 1} color="bg-emerald-500" />
                  <MetricBar label="En erreur" value={stats.documents.failed} max={stats.documents.total || 1} color="bg-red-400" />
                  <div className="pt-2 text-center text-2xl font-bold text-slate-900">{stats.documents.total}</div>
                  <div className="text-center text-xs text-slate-400">documents au total</div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <div className="rounded-lg bg-purple-50 p-2"><MessageSquare size={16} className="text-purple-600" /></div>
                  <span className="text-sm font-medium text-slate-700">Conversations</span>
                </div>
                <div className="space-y-3">
                  <MetricBar label="Ces 7 jours" value={stats.conversations.recent_7d} max={stats.conversations.total || 1} color="bg-purple-500" />
                  <MetricBar label="Questions posées" value={stats.messages.total} max={stats.messages.total || 1} color="bg-brand-500" />
                  <div className="pt-2 text-center text-2xl font-bold text-slate-900">{stats.conversations.total}</div>
                  <div className="text-center text-xs text-slate-400">conversations au total</div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <div className="rounded-lg bg-emerald-50 p-2"><Zap size={16} className="text-emerald-600" /></div>
                  <span className="text-sm font-medium text-slate-700">Performance</span>
                </div>
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-slate-900">
                      {stats.performance.avg_latency_ms ? `${(stats.performance.avg_latency_ms / 1000).toFixed(1)}s` : '-'}
                    </div>
                    <div className="text-xs text-slate-400">Latence moyenne</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-slate-900">
                      {stats.performance.avg_confidence ? `${Math.round(stats.performance.avg_confidence * 100)}%` : '-'}
                    </div>
                    <div className="text-xs text-slate-400">Confiance moyenne</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Activity summary */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-sm font-medium text-slate-700">Activité récente (7 jours)</h2>
              <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
                <div className="text-center">
                  <div className="text-xl font-bold text-brand-600">{stats.messages.recent_7d}</div>
                  <div className="text-xs text-slate-500">Questions</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-purple-600">{stats.conversations.recent_7d}</div>
                  <div className="text-xs text-slate-500">Conversations</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-emerald-600">{stats.documents.indexed}</div>
                  <div className="text-xs text-slate-500">Docs indexés</div>
                </div>
                <div className="text-center">
                  <div className="text-xl font-bold text-amber-600">
                    {stats.performance.avg_latency_ms ? `${(stats.performance.avg_latency_ms / 1000).toFixed(1)}s` : '-'}
                  </div>
                  <div className="text-xs text-slate-500">Latence moy.</div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
