'use client';

import { useEffect, useState, useCallback } from 'react';
import { Upload, FileText, RefreshCw, Trash2, Loader2 } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';
import { cn } from '@/lib/utils';

type Doc = {
  id: string;
  name: string;
  state: string;
  mime_type: string | null;
  tags: string[];
  created_at: string;
};

const STATE_STYLES: Record<string, string> = {
  indexed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  processing: 'bg-amber-50 text-amber-700 border-amber-200',
  uploaded: 'bg-blue-50 text-blue-700 border-blue-200',
  error: 'bg-red-50 text-red-700 border-red-200',
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

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

  async function uploadFileList(files: FileList | File[]) {
    setUploading(true);
    setError(null);
    const names = Array.from(files).map((f) => f.name);
    setUploadFiles(names);
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(file, '', 'member');
      }
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      setUploadFiles([]);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) {
      uploadFileList(e.target.files);
      e.target.value = '';
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) {
      uploadFileList(e.dataTransfer.files);
    }
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function onDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
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
      <div
        className="relative mx-auto max-w-5xl"
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        {/* Drag overlay */}
        {dragging && (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl border-2 border-dashed border-brand-400 bg-brand-50/80 backdrop-blur-sm animate-fade-in">
            <div className="text-center">
              <Upload size={40} className="mx-auto mb-2 animate-bounce text-brand-600" />
              <p className="text-sm font-medium text-brand-700">Drop files here</p>
              <p className="text-xs text-brand-500">PDF, DOCX, Markdown</p>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
            <p className="mt-1 text-sm text-slate-500">{docs.length} document{docs.length !== 1 ? 's' : ''} indexed</p>
          </div>
          <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all duration-150 hover:bg-brand-700 hover:shadow-md">
            <Upload size={16} />
            {uploading ? 'Uploading...' : 'Upload'}
            <input type="file" className="hidden" multiple onChange={onFileChange} disabled={uploading} />
          </label>
        </div>

        {/* Upload progress */}
        {uploading && uploadFiles.length > 0 && (
          <div className="mb-4 space-y-2 rounded-xl border border-brand-200 bg-brand-50 p-4 animate-slide-up">
            {uploadFiles.map((name) => (
              <div key={name} className="flex items-center gap-3">
                <Loader2 size={14} className="animate-spin text-brand-600" />
                <span className="text-sm text-brand-700">{name}</span>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>
        )}

        {/* Table */}
        {docs.length > 0 ? (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50 text-left">
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">Name</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">Type</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">State</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">Created</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {docs.map((d) => (
                  <tr key={d.id} className="transition-colors hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                          <FileText size={14} className="text-slate-500" />
                        </div>
                        <span className="font-medium text-slate-900">{d.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{d.mime_type?.split('/').pop() || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
                        STATE_STYLES[d.state] || 'bg-slate-50 text-slate-600 border-slate-200'
                      )}>
                        {d.state}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500">{new Date(d.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => onReindex(d.id)}
                          className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-brand-600"
                          title="Reindex"
                        >
                          <RefreshCw size={14} />
                        </button>
                        <button
                          onClick={() => onDelete(d.id)}
                          className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-white py-16">
            <div className="mb-3 rounded-full bg-slate-100 p-4">
              <FileText size={24} className="text-slate-400" />
            </div>
            <p className="mb-1 text-sm font-medium text-slate-700">No documents yet</p>
            <p className="mb-4 text-xs text-slate-500">Upload files or drag & drop to get started</p>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700">
              <Upload size={14} />
              Upload files
              <input type="file" className="hidden" multiple onChange={onFileChange} />
            </label>
          </div>
        )}
      </div>
    </AppShell>
  );
}
