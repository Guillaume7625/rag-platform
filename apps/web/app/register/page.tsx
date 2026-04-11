'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api-client';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(false);
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.register(email, password, fullName || undefined);
      if (res.access_token) {
        window.localStorage.setItem('rag_token', res.access_token);
        router.push('/dashboard');
      } else {
        setPending(true);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur lors de l'inscription";
      if (msg.includes('attente') || msg.includes('pending')) {
        setPending(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  if (pending) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="max-w-sm text-center space-y-4">
          <div className="text-5xl">{'\u2709\uFE0F'}</div>
          <h1 className="text-xl font-bold text-stone-900">Demande envoyée</h1>
          <p className="text-sm text-stone-500">
            Votre demande d{"'"}inscription a été transmise à l{"'"}administrateur.
            Vous recevrez un accès dès que votre compte sera validé.
          </p>
          <Link href="/login" className="inline-block text-sm text-blue-600 hover:underline">
            Retour à la connexion
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="text-4xl mb-3">{'\u2728'}</div>
          <h1 className="text-xl font-bold text-stone-900">Créer un compte</h1>
          <p className="mt-1 text-sm text-stone-500">Commencez à explorer vos documents</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-stone-500 uppercase tracking-wide">Nom complet</label>
            <input
              className="mt-1 w-full rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              type="text"
              placeholder="Jean Dupont"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-stone-500 uppercase tracking-wide">Email</label>
            <input
              className="mt-1 w-full rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              placeholder="vous@entreprise.com"
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-stone-500 uppercase tracking-wide">Mot de passe</label>
            <input
              className="mt-1 w-full rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder="Min. 8 caractères"
              minLength={8}
              required
            />
          </div>
          {error && (
            <div className="rounded-md bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-600">{error}</div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Création...' : 'Créer mon compte'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-stone-500">
          Déjà un compte ?{' '}
          <Link href="/login" className="text-blue-600 hover:underline">
            Se connecter
          </Link>
        </div>
      </div>
    </main>
  );
}
