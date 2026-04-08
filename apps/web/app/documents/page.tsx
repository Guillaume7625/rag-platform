'use client';

import { useEffect, useState, useCallback } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Doc = {
  id: string;
  name: string;
  state: string;
  mime_type: string | null;
  tags: string[];
  created_at: string;
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await api.listDocuments();
      setDocs(res.items);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(file, '', 'member');
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  async function onDelete(id: string) {
    if (!confirm('Delete this document?')) return;
    await api.deleteDocument(id);
    refresh();
  }

  async function onReindex(id: string) {
    await api.reindex(id);
    refresh();
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Documents</h1>
          <label className="cursor-pointer rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700">
            {uploading ? 'Uploading…' : 'Upload'}
            <input type="file" className="hidden" onChange={onUpload} disabled={uploading} />
          </label>
        </div>
        {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">State</th>
                <th className="px-4 py-2">Created</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-medium">{d.name}</td>
                  <td className="px-4 py-2">{d.mime_type || '-'}</td>
                  <td className="px-4 py-2">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">
                      {d.state}
                    </span>
                  </td>
                  <td className="px-4 py-2">{new Date(d.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => onReindex(d.id)}
                      className="mr-2 text-brand-600 hover:underline"
                    >
                      Reindex
                    </button>
                    <button
                      onClick={() => onDelete(d.id)}
                      className="text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {docs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                    No documents yet. Upload one above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
