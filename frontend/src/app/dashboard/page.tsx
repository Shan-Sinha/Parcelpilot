'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getUser, clearSession } from '@/lib/api';
import IssuesDashboard from '@/components/IssuesDashboard';
import { Package, LogOut, LayoutDashboard, MessageSquare } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const u = getUser();
    if (!u) {
      router.push('/');
    } else if (u.role === 'customer') {
      router.push('/chat'); // Customers can't access internal dashboard
    } else {
      setUser(u);
    }
  }, [router]);

  if (!user) return null;

  const handleSelectTicket = (ticketId: string) => {
    router.push(`/chat?ticket=${ticketId}`);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      {/* Header Bar */}
      <header style={{
        height: '65px',
        padding: '0 24px',
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              background: '#4f8ef7',
              color: '#fff',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
            }}>
              <Package size={20} />
            </div>
            <div>
              <h1 style={{ fontSize: '16px', fontWeight: 700, color: '#f0f4ff' }}>ParcelPilot AI</h1>
              <p style={{ fontSize: '11px', color: '#8b9fc7' }}>Support & Operations Engine</p>
            </div>
          </div>

          <nav style={{ display: 'flex', gap: '8px', marginLeft: '20px' }}>
            <Link
              href="/chat"
              className="btn btn-ghost"
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              <MessageSquare size={14} /> Agent Chat
            </Link>
            <Link
              href="/dashboard"
              className="btn btn-ghost"
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                background: 'rgba(79, 142, 247, 0.15)',
                color: '#4f8ef7',
                border: '1px solid rgba(79, 142, 247, 0.3)',
              }}
            >
              <LayoutDashboard size={14} /> Proactive Dashboard
            </Link>
          </nav>
        </div>

        <button
          onClick={() => {
            clearSession();
            router.push('/');
          }}
          className="btn btn-ghost"
          style={{ fontSize: '12px', padding: '6px 12px' }}
        >
          <LogOut size={14} /> Sign Out
        </button>
      </header>

      <main style={{ flex: 1 }}>
        <IssuesDashboard onSelectTicket={handleSelectTicket} />
      </main>
    </div>
  );
}
