'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function HomePage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = window.localStorage.getItem('rag_token');
    if (token) {
      router.push('/dashboard');
    } else {
      setChecked(true);
    }
  }, [router]);

  if (!checked) return null;

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-20">
      <div className="max-w-2xl text-center space-y-6">
        <div className="text-6xl">{'\u{1F4C4}'}</div>
        <h1 className="text-5xl font-bold tracking-tight text-stone-900">
          Intelligence documentaire
        </h1>
        <p className="text-lg text-stone-500 max-w-md mx-auto">
          Importez vos documents, posez vos questions, obtenez des réponses avec les sources citées.
        </p>
        <div className="flex items-center justify-center gap-3 pt-4">
          <Link
            href="/register"
            className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Commencer gratuitement →
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-stone-200 bg-white px-5 py-2.5 text-sm font-medium text-stone-700 hover:bg-stone-50 transition-colors"
          >
            Se connecter
          </Link>
        </div>
      </div>

      <div className="mt-20 grid grid-cols-1 gap-4 sm:grid-cols-3 max-w-3xl w-full">
        {[
          { emoji: '\u{1F4E4}', title: 'Importer', desc: 'PDF, Word, PowerPoint, Excel' },
          { emoji: '\u{1F50D}', title: 'Interroger', desc: 'Questions en langage naturel' },
          { emoji: '\u2705', title: 'V\u00e9rifier', desc: 'R\u00e9ponses avec sources cit\u00e9es' },
        ].map((f) => (
          <div key={f.title} className="rounded-lg border border-stone-200/80 p-5 hover:bg-stone-50 transition-colors">
            <div className="text-2xl mb-2">{f.emoji}</div>
            <div className="font-medium text-stone-900">{f.title}</div>
            <div className="text-sm text-stone-500 mt-1">{f.desc}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
