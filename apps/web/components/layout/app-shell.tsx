'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api-client';
import { ErrorBoundary } from '@/components/error-boundary';

const NAV = [
  { href: '/dashboard', label: 'Tableau de bord', emoji: '\u{1F3E0}' },
  { href: '/chat', label: 'Chat', emoji: '\u{1F4AC}' },
  { href: '/documents', label: 'Documents', emoji: '\u{1F4C4}' },
  { href: '/playground', label: 'Playground', emoji: '\u26A1' },
  { href: '/analytics', label: 'Analytics', emoji: '\u{1F4CA}' },
  { href: '/settings', label: 'Param\u00e8tres', emoji: '\u2699\uFE0F' },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState<{ email: string; full_name: string | null } | null>(null);

  useEffect(() => {
    const token = window.localStorage.getItem('rag_token');
    if (!token) {
      router.push('/login');
      return;
    }
    api.me().then((me) => {
      setUser({ email: me.email, full_name: me.full_name ?? null });
      setReady(true);
    }).catch(() => {
      window.localStorage.removeItem('rag_token');
      router.push('/login');
    });
  }, [router]);

  function handleLogout() {
    window.localStorage.removeItem('rag_token');
    router.push('/login');
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
      </div>
    );
  }

  const initials = (user?.full_name || user?.email || '?')[0].toUpperCase();

  const sidebar = (
    <div className="flex h-full w-60 flex-col bg-stone-50 border-r border-stone-200/60">
      {/* Workspace header */}
      <div className="flex items-center gap-2 px-3 py-3">
        <div className="flex h-6 w-6 items-center justify-center rounded text-sm">
          {initials}
        </div>
        <span className="text-sm font-medium text-stone-800 truncate">
          {user?.full_name || 'Mon espace'}
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-1">
        {NAV.map((n) => {
          const active = pathname?.startsWith(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              onClick={() => setSidebarOpen(false)}
              className={cn(
                'group flex items-center gap-2.5 rounded-md px-2 py-1 text-sm transition-colors duration-75',
                active
                  ? 'bg-stone-200/70 text-stone-900'
                  : 'text-stone-500 hover:bg-stone-200/40 hover:text-stone-800',
              )}
            >
              <span className="text-base leading-none w-5 text-center">{n.emoji}</span>
              <span className="truncate">{n.label}</span>
              {active && (
                <ChevronRight size={12} className="ml-auto text-stone-400" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="border-t border-stone-200/60 px-2 py-2">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-stone-200 text-[10px] font-medium text-stone-600">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-stone-700">
              {user?.email}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="rounded p-1 text-stone-400 transition-colors hover:bg-stone-200/60 hover:text-stone-600"
            title="Se d\u00e9connecter"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden md:block shrink-0">
        {sidebar}
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="fixed inset-y-0 left-0 z-50 md:hidden animate-slide-in">
            {sidebar}
          </aside>
        </>
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Mobile header */}
        <header className="flex items-center gap-3 border-b border-stone-200/60 bg-white px-4 py-2.5 md:hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded p-1 text-stone-500 hover:bg-stone-100"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <span className="text-sm font-medium text-stone-700">RAG Platform</span>
        </header>
        <main className="flex-1 px-8 py-6 md:px-12 md:py-8 max-w-5xl">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
