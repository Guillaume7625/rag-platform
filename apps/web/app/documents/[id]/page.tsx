'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { api } from '@/lib/api-client';

type Chunk = {
  id: string;
  order_index: number;
  section_title: string | null;
  content: string;
  token_count: number;
  page: number | null;
};

export default function DocumentChunksPage() {
  const params = useParams();
  const docId = params.id as string;
  const [chunks, setChunks] = useState<Chunk[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDocumentChunks(docId).then((d) => setChunks(d.chunks)).catch((e) => setError(e.message));
  }, [docId]);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <Link href="/documents" className="inline-flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600 mb-2">
            <ChevronLeft size={14} /> Retour aux documents
          </Link>
          <h1 className="text-2xl font-bold text-stone-900">{'\u{1F9E9}'} Segments</h1>
          <p className="mt-1 text-sm text-stone-500">
            {chunks ? `${chunks.length} segments extraits` : 'Chargement...'}
          </p>
        </div>

        {error && <div className="rounded-md bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-600">{error}</div>}

        {!chunks ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg bg-stone-100" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {chunks.map((c, i) => (
              <div key={c.id} className="rounded-lg border border-stone-200/80 bg-white p-4 hover:bg-stone-50 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-stone-100 px-1.5 py-0.5 text-[10px] font-mono text-stone-500">#{i + 1}</span>
                    {c.section_title && (
                      <span className="text-xs font-medium text-stone-700">{c.section_title}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-stone-400">
                    {c.page && <span>p.{c.page}</span>}
                    <span>{c.token_count} tokens</span>
                  </div>
                </div>
                <p className="text-xs text-stone-600 leading-relaxed line-clamp-4">{c.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
