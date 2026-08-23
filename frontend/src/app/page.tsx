'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login, setSession } from '@/lib/api';
import { ShieldCheck, User, ArrowRight, Package } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('northstar');
  const [password, setPassword] = useState('pilot123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (usr?: string, pwd?: string) => {
    const u = usr || username;
    const p = pwd || password;
    setLoading(true);
    setError('');

    // Always clear any existing session before logging in as a new persona
    localStorage.removeItem('pp_token');
    localStorage.removeItem('pp_user');

    try {
      const data = await login(u, p);
      setSession(data.access_token, data.user);
      router.push('/chat');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const personas = [
    {
      id: 'northstar',
      name: 'Northstar Logistics',
      role: 'customer',
      badge: 'Enterprise Customer',
      desc: 'Access scoped exclusively to ACCT-001. Has custom Enterprise Agreement.',
    },
    {
      id: 'lumenworks',
      name: 'LumenWorks',
      role: 'customer',
      badge: 'Service Customer',
      desc: 'Access scoped exclusively to ACCT-002. Has custom Service Agreement.',
    },
    {
      id: 'support',
      name: 'Sam Rivera (Support)',
      role: 'internal',
      badge: 'Internal Agent',
      desc: 'Full operational access to search policies, tickets, and perform state actions.',
    },
    {
      id: 'ops',
      name: 'Morgan Lee (Ops Manager)',
      role: 'ops_manager',
      badge: 'Internal Manager',
      desc: 'Full internal access + Proactive SLA & issue detection dashboard.',
    },
  ];

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      background: 'radial-gradient(circle at 50% 30%, #161c2d 0%, #0a0d14 70%)',
    }}>
      <div style={{ maxWidth: '900px', width: '100%' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px 16px',
            borderRadius: '99px',
            background: 'rgba(79, 142, 247, 0.1)',
            border: '1px solid rgba(79, 142, 247, 0.2)',
            marginBottom: '16px',
          }}>
            <Package size={20} color="#4f8ef7" />
            <span style={{ fontWeight: 700, color: '#f0f4ff', letterSpacing: '0.05em' }}>PARCELPILOT AI</span>
          </div>
          <h1 style={{ fontSize: '32px', fontWeight: 800, color: '#f0f4ff' }}>Customer Support & Operations Platform</h1>
          <p style={{ color: '#8b9fc7', marginTop: '8px', fontSize: '15px' }}>
            Select a persona to test role-based access control, document RAG, and proactive issue detection
          </p>
        </div>

        {/* Persona Selector Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '32px',
        }}>
          {personas.map(p => (
            <div
              key={p.id}
              onClick={() => {
                setUsername(p.id);
                setPassword('pilot123');
                handleLogin(p.id, 'pilot123');
              }}
              className="card fade-in"
              style={{
                padding: '20px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                border: username === p.id ? '1px solid #4f8ef7' : '1px solid var(--border)',
                background: username === p.id ? 'rgba(79, 142, 247, 0.08)' : 'var(--bg-card)',
                boxShadow: username === p.id ? '0 0 20px rgba(79,142,247,0.2)' : 'var(--shadow-card)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <User size={20} color={p.role === 'customer' ? '#a78bfa' : '#4f8ef7'} />
                <span className={`badge ${p.role === 'customer' ? 'badge-contract' : 'badge-policy'}`} style={{ fontSize: '10px' }}>
                  {p.badge}
                </span>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f4ff', marginBottom: '4px' }}>{p.name}</h3>
              <p style={{ fontSize: '12px', color: '#8b9fc7', lineHeight: 1.4 }}>{p.desc}</p>
              <div style={{
                marginTop: '16px',
                fontSize: '12px',
                color: '#4f8ef7',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}>
                Launch Session <ArrowRight size={14} />
              </div>
            </div>
          ))}
        </div>

        {/* Manual Login Form */}
        <div className="card" style={{ padding: '24px', maxWidth: '400px', margin: '0 auto' }}>
          <h3 style={{ fontSize: '16px', color: '#f0f4ff', marginBottom: '16px', textAlign: 'center' }}>
            Or Sign In Manually
          </h3>

          {error && (
            <div style={{
              background: 'rgba(248,113,113,0.15)',
              border: '1px solid rgba(248,113,113,0.3)',
              color: '#f87171',
              padding: '10px',
              borderRadius: '8px',
              fontSize: '13px',
              marginBottom: '16px',
            }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#8b9fc7', display: 'block', marginBottom: '4px' }}>Username</label>
              <input
                type="text"
                className="input"
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#8b9fc7', display: 'block', marginBottom: '4px' }}>Password</label>
              <input
                type="password"
                className="input"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>
            <button
              onClick={() => handleLogin()}
              disabled={loading}
              className="btn btn-primary"
              style={{ marginTop: '8px', width: '100%', justifyContent: 'center', padding: '10px' }}
            >
              {loading ? <div className="spinner" /> : 'Sign In'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
