'use client';

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, Shield, AlertCircle, FileText, Database, Wrench, Sparkles } from 'lucide-react';
import { sendChat, confirmAction, Message } from '@/lib/api';
import ToolCallCard from './ToolCallCard';
import ConfirmationModal from './ConfirmationModal';

interface ChatInterfaceProps {
  user: {
    username: string;
    full_name: string;
    role: string;
    account_id?: string;
    account_name?: string;
  };
  initialQuery?: string;
}

export default function ChatInterface({ user, initialQuery }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: user.role === 'customer'
        ? `Hello **${user.full_name}**! I am your ParcelPilot Support Assistant.\n\nI can help you check order statuses, answer questions about your **${user.account_name}** contract terms, policy details, service credits, or request cancellations. How can I assist you today?`
        : `Welcome **${user.full_name}** (Internal ${user.role}).\n\nI have full operational access across all accounts, orders, support policies, and ticket history. Ask me any question, request complex multi-step investigations, or ask me to prepare ticket updates/escalations.`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [toolCalls, setToolCalls] = useState<any[]>([]);
  const [pendingConfirmation, setPendingConfirmation] = useState<any | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, toolCalls, loading]);

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: user.role === 'customer'
          ? `Hello **${user.full_name}**! I am your ParcelPilot Support Assistant.\n\nI can help you check order statuses, answer questions about your **${user.account_name}** contract terms, policy details, service credits, or request cancellations. How can I assist you today?`
          : `Welcome **${user.full_name}** (Internal ${user.role}).\n\nI have full operational access across all accounts, orders, support policies, and ticket history. Ask me any question, request complex multi-step investigations, or ask me to prepare ticket updates/escalations.`,
      },
    ]);
    setToolCalls([]);
    setPendingConfirmation(null);
  }, [user.username]);

  useEffect(() => {
    if (initialQuery) {
      handleSend(initialQuery);
    }
  }, [initialQuery]);

  const handleSend = async (textToSend?: string) => {
    const queryText = textToSend || input;
    if (!queryText.trim() || loading) return;

    const newMessages: Message[] = [...messages, { role: 'user', content: queryText }];
    setMessages(newMessages);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      // Send message to backend
      const res = await sendChat(newMessages);

      if (res.tool_calls && res.tool_calls.length > 0) {
        setToolCalls(prev => [...prev, ...res.tool_calls]);
      }

      if (res.requires_confirmation) {
        setPendingConfirmation(res.requires_confirmation);
      }

      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: res.message || 'Action prepared. Please review and confirm.' },
      ]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `⚠️ **Error:** ${err.message || 'Failed to process request.'}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAction = async () => {
    if (!pendingConfirmation) return;
    setConfirmLoading(true);

    try {
      const res = await confirmAction(
        pendingConfirmation.action_type,
        pendingConfirmation.details,
        pendingConfirmation.reason || ''
      );

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `✅ **Action Executed Successfully!**\n\n\`\`\`json\n${JSON.stringify(res.result, null, 2)}\n\`\`\``,
        },
      ]);
      setPendingConfirmation(null);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `❌ **Action Failed:** ${err.message}` },
      ]);
    } finally {
      setConfirmLoading(false);
    }
  };

  // Account-specific prompt chips
  const samplePrompts = user.username === 'northstar'
    ? [
        'Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.',
        'Check status of order ORD-1001 and ORD-1002.',
        'What is our SLA for critical priority support tickets?',
        'Show my open support tickets.',
      ]
    : user.username === 'lumenworks'
    ? [
        'A pickup is 3 hours late due to carrier fault. Am I eligible for a service credit?',
        'Why did our bulk upload fail for ticket TKT-502?',
        'Check status of order ORD-2001.',
        'Show my open support tickets.',
      ]
    : user.role === 'customer'
    ? [
        'Show my open support tickets.',
        'Check status of my recent orders.',
        'What are our contract support SLA terms?',
      ]
    : [
        'Can Northstar cancel ORD-1001 without a cancellation fee? Check agreement and SOP.',
        'Investigate ticket TKT-501 and tell me if the resolution follows current policy v3.',
        'Check all open tickets for LumenWorks and calculate SLA breach risk.',
        'Create an escalation for ticket TKT-505 due to security issue.',
      ];

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 65px)', width: '100%' }}>
      {/* Main Chat Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        borderRight: '1px solid var(--border)',
        background: 'var(--bg-base)',
      }}>
        {/* User Context Banner */}
        <div style={{
          padding: '12px 20px',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justify: 'space-between',
          alignItems: 'center',
          fontSize: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <User size={14} color="#4f8ef7" />
            <span style={{ color: '#f0f4ff', fontWeight: 600 }}>{user.full_name}</span>
            <span className={`badge ${user.role === 'customer' ? 'badge-contract' : 'badge-policy'}`}>
              {user.role === 'customer' ? `Account: ${user.account_name}` : `Role: ${user.role}`}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#8b9fc7' }}>
              <Shield size={12} color="#34d399" />
              <span>Data Access: <strong>{user.role === 'customer' ? 'Scoped to Account' : 'Full Internal'}</strong></span>
            </div>
            <button
              onClick={() => {
                setMessages([
                  {
                    role: 'assistant',
                    content: user.role === 'customer'
                      ? `Hello **${user.full_name}**! I am your ParcelPilot Support Assistant.\n\nI can help you check order statuses, answer questions about your **${user.account_name}** contract terms, policy details, service credits, or request cancellations. How can I assist you today?`
                      : `Welcome **${user.full_name}** (Internal ${user.role}).\n\nI have full operational access across all accounts, orders, support policies, and ticket history. Ask me any question, request complex multi-step investigations, or ask me to prepare ticket updates/escalations.`,
                  },
                ]);
                setToolCalls([]);
                setPendingConfirmation(null);
              }}
              className="btn btn-ghost"
              style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '6px', border: '1px solid var(--border)' }}
            >
              New Conversation
            </button>
          </div>
        </div>

        {/* Message Stream */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}>
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className="fade-in"
              style={{
                display: 'flex',
                gap: '12px',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
              }}
            >
              {msg.role === 'assistant' && (
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #4f8ef7, #a78bfa)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  boxShadow: '0 0 12px rgba(79,142,247,0.3)',
                }}>
                  <Bot size={18} color="#fff" />
                </div>
              )}

              <div style={{
                background: msg.role === 'user' ? '#1e2640' : 'var(--bg-card)',
                border: `1px solid ${msg.role === 'user' ? 'rgba(79,142,247,0.3)' : 'var(--border)'}`,
                borderRadius: msg.role === 'user' ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                padding: '14px 18px',
                boxShadow: 'var(--shadow-card)',
              }}>
                {msg.role === 'assistant' ? (
                  <div className="prose">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div style={{ color: '#f0f4ff', whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                )}
              </div>

              {msg.role === 'user' && (
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <User size={16} color="#8b9fc7" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', gap: '12px', alignSelf: 'flex-start' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #4f8ef7, #a78bfa)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Bot size={18} color="#fff" />
              </div>
              <div className="card" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '13px', color: '#8b9fc7' }}>Reasoning & retrieving tools...</span>
                <div className="thinking-dots" style={{ display: 'flex', gap: '4px' }}>
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Sample Prompt Chips */}
        <div style={{ padding: '0 20px 8px', display: 'flex', gap: '8px', overflowX: 'auto' }}>
          {samplePrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => handleSend(p)}
              disabled={loading}
              className="btn btn-ghost"
              style={{
                fontSize: '11px',
                padding: '4px 10px',
                borderRadius: '99px',
                whiteSpace: 'nowrap',
                background: 'rgba(255,255,255,0.02)',
              }}
            >
              <Sparkles size={10} color="#4f8ef7" /> {p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div style={{
          padding: '16px 20px',
          background: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          gap: '10px',
        }}>
          <input
            type="text"
            className="input"
            placeholder={user.role === 'customer' ? 'Ask about orders, policies, credits...' : 'Ask question or command operational workflow...'}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="btn btn-primary"
            style={{ padding: '0 20px' }}
          >
            {loading ? <div className="spinner" /> : <Send size={16} />}
          </button>
        </div>
      </div>

      {/* Right Sidebar: Agent Activity & Tool Trace */}
      <div style={{
        width: '380px',
        background: 'var(--bg-surface)',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px',
        overflowY: 'auto',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          paddingBottom: '12px',
          marginBottom: '12px',
          borderBottom: '1px solid var(--border)',
        }}>
          <Wrench size={16} color="#4f8ef7" />
          <h3 style={{ fontSize: '14px', color: '#f0f4ff', fontWeight: 600 }}>Agent Tool Call Inspector</h3>
        </div>

        <p style={{ fontSize: '12px', color: '#8b9fc7', marginBottom: '16px' }}>
          Real-time execution log showing multi-step reasoning, ChromaDB vector retrieval, SQLite queries, and source reliability ranking.
        </p>

        {toolCalls.length === 0 ? (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#4a5568',
            textAlign: 'center',
            gap: '8px',
          }}>
            <Database size={32} />
            <span style={{ fontSize: '13px' }}>No tools invoked yet</span>
            <span style={{ fontSize: '11px' }}>Ask a question to see the agent reasoning trace</span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {toolCalls.map((tc, idx) => (
              <ToolCallCard key={idx} toolCall={tc} />
            ))}
          </div>
        )}
      </div>

      {/* Confirmation Modal overlay when action requires approval */}
      {pendingConfirmation && (
        <ConfirmationModal
          action={pendingConfirmation}
          onConfirm={handleConfirmAction}
          onCancel={() => setPendingConfirmation(null)}
          isLoading={confirmLoading}
        />
      )}
    </div>
  );
}
