import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6">
      <div className="space-y-3">
        <h1 className="text-4xl font-bold">RAG Platform</h1>
        <p className="text-slate-600">
          Multi-tenant document intelligence with hybrid retrieval, reranking,
          and citation-grounded generation.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          className="rounded-md bg-brand-600 px-4 py-2 text-white hover:bg-brand-700"
          href="/login"
        >
          Sign in
        </Link>
        <Link
          className="rounded-md border border-slate-300 px-4 py-2 hover:bg-white"
          href="/chat"
        >
          Open chat
        </Link>
      </div>
    </main>
  );
}
