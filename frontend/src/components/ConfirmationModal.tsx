'use client';

import React from 'react';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

interface ConfirmationModalProps {
  action: {
    action_type: string;
    details: Record<string, any>;
    reason?: string;
    summary?: string;
  };
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export default function ConfirmationModal({
  action,
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmationModalProps) {
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px',
    }}>
      <div className="card fade-in" style={{
        maxWidth: '520px',
        width: '100%',
        padding: '24px',
        background: '#161c2d',
        border: '1px solid rgba(251, 191, 36, 0.4)',
        boxShadow: '0 0 32px rgba(251, 191, 36, 0.15)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <div style={{
            background: 'rgba(251, 191, 36, 0.15)',
            color: '#fbbf24',
            padding: '10px',
            borderRadius: '12px',
            display: 'flex',
          }}>
            <AlertTriangle size={24} />
          </div>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#f0f4ff' }}>Action Confirmation Required</h3>
            <p style={{ fontSize: '13px', color: '#8b9fc7' }}>This action will modify data in ParcelPilot</p>
          </div>
        </div>

        <div style={{
          background: 'rgba(10, 13, 20, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '10px',
          padding: '16px',
          marginBottom: '20px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 500, color: '#f0f4ff', marginBottom: '8px' }}>
            Summary:
          </div>
          <div style={{ fontSize: '13px', color: '#fbbf24', lineHeight: 1.5, marginBottom: '12px' }}>
            {action.summary || `${action.action_type} on ${JSON.stringify(action.details)}`}
          </div>

          <div style={{ fontSize: '12px', color: '#8b9fc7', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div><strong>Action Type:</strong> <code style={{ color: '#4f8ef7' }}>{action.action_type}</code></div>
            <div><strong>Details:</strong> <code style={{ color: '#8b9fc7' }}>{JSON.stringify(action.details, null, 2)}</code></div>
            {action.reason && <div><strong>Reason:</strong> {action.reason}</div>}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="btn btn-ghost"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <XCircle size={16} />
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="btn btn-primary"
            style={{
              background: '#fbbf24',
              color: '#0a0d14',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {isLoading ? (
              <span className="spinner" style={{ borderTopColor: '#0a0d14' }}></span>
            ) : (
              <CheckCircle size={16} />
            )}
            Confirm & Execute
          </button>
        </div>
      </div>
    </div>
  );
}
