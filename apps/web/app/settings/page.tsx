'use client';

import { useEffect, useState } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

export default function SettingsPage() {
  const [me, setMe] = useState<{ email: string; tenant_id: string; role: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then(setMe)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-4">
        <h1 className="text-2xl font-semibold">Settings</h1>
        {error && <div className="text-sm text-red-600">{error}</div>}
        {me && (
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <div>
              <span className="text-slate-500">Email:</span> {me.email}
            </div>
            <div>
              <span className="text-slate-500">Tenant:</span> {me.tenant_id}
            </div>
            <div>
              <span className="text-slate-500">Role:</span> {me.role}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
