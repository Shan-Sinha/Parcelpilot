'use client';

import React, { useEffect, useState } from 'react';
import { getProactiveIssues } from '@/lib/api';
import { AlertOctagon, AlertTriangle, TrendingUp, Users, Clock, RefreshCw, ShieldAlert, CheckCircle } from 'lucide-react';

interface Issue {
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  ticket_id?: string;
  account_id?: string;
  age_hours?: number;
  category?: string;
  count?: number;
}

interface IssuesDashboardProps {
  onSelectTicket?: (ticketId: string) => void;
}

export default function IssuesDashboard({ onSelectTicket }: IssuesDashboardProps) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const fetchIssues = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProactiveIssues();
      setIssues(data.issues || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load proactive issues');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIssues();
  }, []);

  const filteredIssues = issues.filter(issue => {
    if (filter === 'all') return true;
    return issue.severity === filter;
  });

  const getIcon = (type: string, severity: string) => {
    if (severity === 'critical') return <AlertOctagon size={18} color="#f87171" />;
    if (type === 'sla_warning') return <Clock size={18} color="#fbbf24" />;
    if (type === 'ticket_surge') return <TrendingUp size={18} color="#a78bfa" />;
    if (type === 'account_multi_ticket') return <Users size={18} color="#4f8ef7" />;
    return <AlertTriangle size={18} color="#fbbf24" />;
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#f0f4ff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert color="#4f8ef7" size={26} />
            Proactive Operations Dashboard
          </h2>
          <p style={{ color: '#8b9fc7', fontSize: '14px', marginTop: '4px' }}>
            Real-time issue detection across SLA risks, ticket surges, and account customer health
          </p>
        </div>
        <button
          onClick={fetchIssues}
          disabled={loading}
          className="btn btn-ghost"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          Refresh Detection
        </button>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ color: '#8b9fc7', fontSize: '12px', fontWeight: 600 }}>TOTAL DETECTED ISSUES</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#f0f4ff', marginTop: '4px' }}>{issues.length}</div>
        </div>
        <div className="card" style={{ padding: '16px', borderColor: 'rgba(248, 113, 113, 0.3)' }}>
          <div style={{ color: '#f87171', fontSize: '12px', fontWeight: 600 }}>CRITICAL SLA BREACHES</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#f87171', marginTop: '4px' }}>
            {issues.filter(i => i.severity === 'critical').length}
          </div>
        </div>
        <div className="card" style={{ padding: '16px', borderColor: 'rgba(251, 191, 36, 0.3)' }}>
          <div style={{ color: '#fbbf24', fontSize: '12px', fontWeight: 600 }}>SLA WARNINGS & RISKS</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fbbf24', marginTop: '4px' }}>
            {issues.filter(i => i.severity === 'high').length}
          </div>
        </div>
        <div className="card" style={{ padding: '16px', borderColor: 'rgba(167, 139, 250, 0.3)' }}>
          <div style={{ color: '#a78bfa', fontSize: '12px', fontWeight: 600 }}>CATEGORY SURGES</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#a78bfa', marginTop: '4px' }}>
            {issues.filter(i => i.type === 'ticket_surge').length}
          </div>
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {['all', 'critical', 'high', 'medium'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`btn ${filter === f ? 'btn-primary' : 'btn-ghost'}`}
            style={{ textTransform: 'capitalize', fontSize: '12px', padding: '6px 14px' }}
          >
            {f} {f !== 'all' && `(${issues.filter(i => i.severity === f).length})`}
          </button>
        ))}
      </div>

      {/* Issues list */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
          <div className="spinner" style={{ width: '32px', height: '32px' }}></div>
        </div>
      ) : error ? (
        <div className="card" style={{ padding: '20px', color: '#f87171', background: 'rgba(248,113,113,0.1)' }}>
          {error}
        </div>
      ) : filteredIssues.length === 0 ? (
        <div className="card" style={{ padding: '40px', textAlign: 'center', color: '#8b9fc7' }}>
          <CheckCircle size={36} color="#34d399" style={{ margin: '0 auto 12px' }} />
          <h3>All Clear</h3>
          <p style={{ marginTop: '4px' }}>No operational issues detected in this category</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredIssues.map((issue, idx) => (
            <div
              key={idx}
              className="card fade-in"
              style={{
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderLeft: `4px solid ${
                  issue.severity === 'critical' ? '#f87171' :
                  issue.severity === 'high' ? '#fbbf24' : '#a78bfa'
                }`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                <div style={{ marginTop: '2px' }}>
                  {getIcon(issue.type, issue.severity)}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <h4 style={{ fontSize: '15px', color: '#f0f4ff' }}>{issue.title}</h4>
                    <span className={`badge badge-${issue.severity}`}>
                      {issue.severity}
                    </span>
                    <span className="badge badge-policy" style={{ fontSize: '10px' }}>
                      {issue.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p style={{ fontSize: '13px', color: '#8b9fc7' }}>{issue.description}</p>
                </div>
              </div>

              {issue.ticket_id && onSelectTicket && (
                <button
                  onClick={() => onSelectTicket(issue.ticket_id!)}
                  className="btn btn-ghost"
                  style={{ fontSize: '12px' }}
                >
                  Investigate Ticket →
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
