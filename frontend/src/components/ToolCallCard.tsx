'use client';

import React, { useState } from 'react';
import { Search, Database, ShieldAlert, ChevronDown, ChevronUp, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

interface ToolCall {
  tool: string;
  input: Record<string, any>;
  output: any;
}

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getToolMeta = () => {
    switch (toolCall.tool) {
      case 'search_documents':
        return {
          icon: <Search size={14} color="#4f8ef7" />,
          label: 'Document Search (RAG)',
          badgeColor: 'badge-policy',
          summary: toolCall.input?.query || 'Document search',
        };
      case 'lookup_data':
        return {
          icon: <Database size={14} color="#34d399" />,
          label: 'Structured Data Lookup',
          badgeColor: 'badge-sop',
          summary: `${toolCall.input?.entity || 'data'} query`,
        };
      case 'create_action':
        return {
          icon: <ShieldAlert size={14} color="#fbbf24" />,
          label: 'State-Changing Action',
          badgeColor: 'badge-guide',
          summary: `${toolCall.input?.action_type || 'action'} prepared`,
        };
      default:
        return {
          icon: <FileText size={14} color="#a78bfa" />,
          label: toolCall.tool,
          badgeColor: 'badge-policy',
          summary: 'Tool invocation',
        };
    }
  };

  const meta = getToolMeta();

  return (
    <div style={{
      background: 'rgba(17, 21, 32, 0.7)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      borderRadius: '8px',
      marginBottom: '8px',
      overflow: 'hidden',
      fontSize: '12px',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none',
          background: expanded ? 'rgba(30, 38, 64, 0.5)' : 'transparent',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {meta.icon}
          <span style={{ fontWeight: 600, color: '#f0f4ff' }}>{meta.label}</span>
          <span className={`badge ${meta.badgeColor}`} style={{ fontSize: '10px', padding: '1px 6px' }}>
            {toolCall.tool}
          </span>
          <span style={{ color: '#8b9fc7', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            "{meta.summary}"
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#8b9fc7' }}>
          {toolCall.output?.confirmation_required ? (
            <span style={{ color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertCircle size={12} /> Pending Approval
            </span>
          ) : (
            <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={12} /> Executed
            </span>
          )}
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {expanded && (
        <div style={{ padding: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.05)', background: 'rgba(10, 13, 20, 0.5)' }}>
          <div style={{ marginBottom: '10px' }}>
            <div style={{ color: '#8b9fc7', fontWeight: 600, marginBottom: '4px' }}>Input Arguments:</div>
            <pre style={{
              background: '#0a0d14',
              padding: '8px',
              borderRadius: '6px',
              fontSize: '11px',
              color: '#4f8ef7',
              overflowX: 'auto',
            }}>
              {JSON.stringify(toolCall.input, null, 2)}
            </pre>
          </div>

          <div>
            <div style={{ color: '#8b9fc7', fontWeight: 600, marginBottom: '4px' }}>Output / Result:</div>
            <pre style={{
              background: '#0a0d14',
              padding: '8px',
              borderRadius: '6px',
              fontSize: '11px',
              color: '#34d399',
              maxHeight: '180px',
              overflowY: 'auto',
              overflowX: 'auto',
            }}>
              {typeof toolCall.output === 'object'
                ? JSON.stringify(toolCall.output, null, 2)
                : String(toolCall.output)}
            </pre>
          </div>

          {/* Sources preview if present */}
          {toolCall.output?.sources && toolCall.output.sources.length > 0 && (
            <div style={{ marginTop: '10px' }}>
              <div style={{ color: '#8b9fc7', fontWeight: 600, marginBottom: '6px' }}>Retrieved Sources:</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {toolCall.output.sources.map((s: any, idx: number) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '4px 8px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: '4px',
                    fontSize: '11px',
                  }}>
                    <span style={{ color: '#f0f4ff' }}>{s.source_label}</span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {s.is_deprecated && (
                        <span className="badge badge-deprecated" style={{ fontSize: '9px' }}>DEPRECATED</span>
                      )}
                      <span className={`badge badge-${s.badge}`} style={{ fontSize: '9px' }}>
                        Trust: {s.trust}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
