'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { User, Building2, Shield, LogOut } from 'lucide-react';
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

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="text-2xl font-semibold">Settings</h1>
        {error && <div className="text-sm text-red-600">{error}</div>}
        {me && (
          <>
            <div className="rounded-lg border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                Profile
              </div>
              <div className="divide-y divide-slate-100">
                <div className="flex items-center gap-3 px-4 py-3">
                  <User size={16} className="text-slate-400" />
                  <div>
                    <div className="text-xs text-slate-500">Name</div>
                    <div className="text-sm">{me.full_name || 'Not set'}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 px-4 py-3">
                  <User size={16} className="text-slate-400" />
                  <div>
                    <div className="text-xs text-slate-500">Email</div>
                    <div className="text-sm">{me.email}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 px-4 py-3">
                  <Shield size={16} className="text-slate-400" />
                  <div>
                    <div className="text-xs text-slate-500">Role</div>
                    <div className="text-sm capitalize">{me.role}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 px-4 py-3">
                  <Building2 size={16} className="text-slate-400" />
                  <div>
                    <div className="text-xs text-slate-500">Workspace</div>
                    <div className="text-sm font-mono text-slate-600 text-xs">{me.tenant_id.slice(0, 8)}</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-red-200 bg-white">
              <div className="border-b border-red-100 px-4 py-3 text-xs font-medium uppercase tracking-wide text-red-500">
                Danger zone
              </div>
              <div className="px-4 py-3">
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
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
