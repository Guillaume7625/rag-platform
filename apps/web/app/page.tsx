'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { MessageSquare, FileText, Shield, ArrowRight } from 'lucide-react';

const FEATURES = [
  {
    icon: FileText,
    title: 'Upload',
    description: 'PDF, DOCX, Markdown — drag & drop or browse',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    icon: MessageSquare,
    title: 'Ask',
    description: 'Natural language queries across all your documents',
    color: 'bg-purple-50 text-purple-600',
  },
  {
    icon: Shield,
    title: 'Trust',
    description: 'Every answer cites its sources with page references',
    color: 'bg-emerald-50 text-emerald-600',
  },
];

export default function HomePage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = window.localStorage.getItem('rag_token');
    if (token) {
      router.push('/chat');
    } else {
      setChecked(true);
    }
  }, [router]);

  if (!checked) return null;

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50">
      <div className="mx-auto flex max-w-4xl flex-col items-center justify-center gap-16 px-6 py-24">
        {/* Hero */}
        <div className="space-y-6 text-center animate-slide-up">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-4 py-1.5 text-xs font-medium text-brand-700">
            Powered by hybrid RAG
          </div>
          <h1 className="text-5xl font-bold tracking-tight text-slate-900">
            Document intelligence
            <br />
            <span className="text-brand-600">you can trust</span>
          </h1>
          <p className="mx-auto max-w-lg text-lg text-slate-500">
            Upload documents, ask questions in natural language, get answers grounded in your data with cited sources.
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-3">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="group rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md animate-slide-up"
                style={{ animationDelay: `${i * 100}ms`, animationFillMode: 'both' }}
              >
                <div className={`mb-4 inline-flex rounded-lg p-2.5 ${f.color}`}>
                  <Icon size={20} />
                </div>
                <h3 className="mb-1 font-semibold text-slate-900">{f.title}</h3>
                <p className="text-sm text-slate-500">{f.description}</p>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div className="flex gap-4 animate-slide-up" style={{ animationDelay: '300ms', animationFillMode: 'both' }}>
          <Link
            href="/register"
            className="group flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-3 font-medium text-white shadow-lg shadow-brand-600/25 transition-all duration-200 hover:bg-brand-700 hover:shadow-xl hover:shadow-brand-600/30"
          >
            Get started
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href="/login"
            className="rounded-xl border border-slate-200 bg-white px-6 py-3 font-medium text-slate-700 shadow-sm transition-all duration-200 hover:border-slate-300 hover:shadow-md"
          >
            Sign in
          </Link>
        </div>
      </div>
    </main>
  );
}
