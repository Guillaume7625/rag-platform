import Link from 'next/link';
import { MessageSquare, FileText, Shield } from 'lucide-react';

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-10 px-6">
      <div className="space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">RAG Platform</h1>
        <p className="text-lg text-slate-600">
          Upload documents, ask questions in natural language, get answers with cited sources.
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <FileText size={20} className="mb-2 text-brand-600" />
          <div className="text-sm font-medium">Upload</div>
          <div className="text-xs text-slate-500">PDF, DOCX, Markdown</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <MessageSquare size={20} className="mb-2 text-brand-600" />
          <div className="text-sm font-medium">Ask</div>
          <div className="text-xs text-slate-500">Natural language queries</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <Shield size={20} className="mb-2 text-brand-600" />
          <div className="text-sm font-medium">Trust</div>
          <div className="text-xs text-slate-500">Cited, grounded answers</div>
        </div>
      </div>
      <div className="flex gap-3">
        <Link
          className="rounded-md bg-brand-600 px-5 py-2.5 text-white hover:bg-brand-700 font-medium"
          href="/register"
        >
          Get started
        </Link>
        <Link
          className="rounded-md border border-slate-300 px-5 py-2.5 hover:bg-white font-medium"
          href="/login"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
