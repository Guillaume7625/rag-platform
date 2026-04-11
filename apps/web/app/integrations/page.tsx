'use client';

import { useState } from 'react';
import { AppShell } from '@/components/layout/app-shell';

export default function IntegrationsPage() {
  const [copied, setCopied] = useState<string | null>(null);

  function copy(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  const widgetCode = `<script>
  window.RAG_WIDGET_URL = "https://rag.marinenationale.cloud";
  window.RAG_WIDGET_TOKEN = "VOTRE_TOKEN_JWT";
</script>
<script src="https://rag.marinenationale.cloud/widget.js"></script>`;

  const apiExample = `curl -X POST https://rag.marinenationale.cloud/api/chat/query \\
  -H "Authorization: Bearer VOTRE_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Votre question ici"}'`;

  return (
    <AppShell>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-stone-900">{'\u{1F517}'} Int&eacute;grations</h1>
          <p className="mt-1 text-stone-500">Int&eacute;grez le RAG dans vos outils</p>
        </div>

        {/* Widget */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-stone-500">{'\u{1F4AC}'} Widget chat</h2>
          <p className="text-xs text-stone-400">Copiez ce code dans votre site pour ajouter un assistant flottant.</p>
          <div className="relative rounded-lg bg-stone-900 p-4">
            <pre className="text-xs text-green-400 overflow-x-auto whitespace-pre">{widgetCode}</pre>
            <button
              onClick={() => copy(widgetCode, 'widget')}
              className="absolute top-2 right-2 rounded bg-stone-700 px-2 py-1 text-[10px] text-stone-300 hover:bg-stone-600"
            >
              {copied === 'widget' ? '\u2713 Copié' : 'Copier'}
            </button>
          </div>
        </div>

        {/* API */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-stone-500">{'\u{1F527}'} API REST</h2>
          <p className="text-xs text-stone-400">Appelez le moteur RAG depuis vos applications.</p>
          <div className="relative rounded-lg bg-stone-900 p-4">
            <pre className="text-xs text-green-400 overflow-x-auto whitespace-pre">{apiExample}</pre>
            <button
              onClick={() => copy(apiExample, 'api')}
              className="absolute top-2 right-2 rounded bg-stone-700 px-2 py-1 text-[10px] text-stone-300 hover:bg-stone-600"
            >
              {copied === 'api' ? '\u2713 Copié' : 'Copier'}
            </button>
          </div>
        </div>

        {/* Endpoints */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-stone-500">{'\u{1F4CB}'} Endpoints disponibles</h2>
          <div className="rounded-lg border border-stone-200/80 bg-white overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-stone-100 bg-stone-50">
                  <th className="px-4 py-2 text-left text-stone-500 font-medium">M&eacute;thode</th>
                  <th className="px-4 py-2 text-left text-stone-500 font-medium">Endpoint</th>
                  <th className="px-4 py-2 text-left text-stone-500 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {[
                  { method: 'POST', path: '/api/chat/query', desc: 'Poser une question (JSON)' },
                  { method: 'POST', path: '/api/chat/stream', desc: 'Poser une question (SSE streaming)' },
                  { method: 'POST', path: '/api/documents/upload', desc: 'Importer un document' },
                  { method: 'GET', path: '/api/documents', desc: 'Lister les documents' },
                  { method: 'GET', path: '/api/conversations', desc: 'Lister les conversations' },
                  { method: 'GET', path: '/api/stats/dashboard', desc: 'Statistiques du tableau de bord' },
                  { method: 'POST', path: '/api/auth/login', desc: 'Obtenir un token JWT' },
                  { method: 'POST', path: '/api/auth/register', desc: 'Créer un compte' },
                ].map((e) => (
                  <tr key={e.path} className="hover:bg-stone-50">
                    <td className="px-4 py-2"><span className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${e.method === 'GET' ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'}`}>{e.method}</span></td>
                    <td className="px-4 py-2 font-mono text-stone-700">{e.path}</td>
                    <td className="px-4 py-2 text-stone-500">{e.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
