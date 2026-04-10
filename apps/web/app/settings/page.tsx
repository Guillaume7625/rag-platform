'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Mail, Shield, Building2, LogOut } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

export default function SettingsPage() {
  const [me, setMe] = useState<{ email: string; full_name: string | null; tenant_id: string; role: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    api
      .me()
      .then(setMe)
      .catch((err) => setError(err.message));
  }, []);

  function handleLogout() {
    window.localStorage.removeItem('rag_token');
    router.push('/login');
  }

  const initials = (me?.full_name || me?.email || '?')[0].toUpperCase();

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
        {me && (
          <>
            {/* Profile header */}
            <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm animate-slide-up">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-bold text-white shadow-lg shadow-brand-600/25">
                {initials}
              </div>
              <div>
                <div className="text-lg font-semibold text-slate-900">{me.full_name || 'User'}</div>
                <div className="text-sm text-slate-500">{me.email}</div>
              </div>
            </div>

            {/* Details */}
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm animate-slide-up" style={{ animationDelay: '100ms', animationFillMode: 'both' }}>
              <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-3">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Account details</span>
              </div>
              <div className="divide-y divide-slate-100">
                {[
                  { icon: Mail, label: 'Email', value: me.email },
                  { icon: Shield, label: 'Role', value: me.role.charAt(0).toUpperCase() + me.role.slice(1) },
                  { icon: Building2, label: 'Workspace', value: me.tenant_id.slice(0, 8) },
                ].map((row) => (
                  <div key={row.label} className="flex items-center gap-4 px-6 py-4 transition-colors hover:bg-slate-50">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                      <row.icon size={16} className="text-slate-500" />
                    </div>
                    <div>
                      <div className="text-xs text-slate-500">{row.label}</div>
                      <div className="text-sm font-medium text-slate-900">{row.value}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Danger zone */}
            <div className="overflow-hidden rounded-xl border border-red-100 bg-white shadow-sm animate-slide-up" style={{ animationDelay: '200ms', animationFillMode: 'both' }}>
              <div className="border-b border-red-100 bg-red-50/50 px-6 py-3">
                <span className="text-xs font-medium uppercase tracking-wide text-red-500">Danger zone</span>
              </div>
              <div className="px-6 py-4">
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 transition-all duration-150 hover:bg-red-50 hover:shadow-sm"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
