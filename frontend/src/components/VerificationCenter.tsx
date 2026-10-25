import React from 'react';
import { ShieldCheck, CheckCircle2, AlertTriangle, FileSearch, Layers, Sparkles } from 'lucide-react';

export const VerificationCenter: React.FC = () => {
  return (
    <div style={{ maxWidth: 1200, margin: '24px auto', padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="glass-panel" style={{ padding: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#10b981',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <ShieldCheck size={26} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
              Evidence & Answer Verification Architecture
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
              Multi-stage hallucination mitigation and grounding verification.
            </p>
          </div>
        </div>
      </div>

      {/* 3-Stage Verification Pipeline Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
        <div className="glass-panel" style={{ padding: 22 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: 'var(--accent-cyan)' }}>
            <FileSearch size={20} />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>1. Context Verification</h3>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
            Evaluates retrieved document chunks <em>before</em> answer generation. Assesses whether evidence is <strong>SUFFICIENT</strong>, <strong>PARTIALLY SUFFICIENT</strong>, or <strong>INSUFFICIENT</strong>, and actively checks for conflicting statements across document versions.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span className="badge badge-verified">Relevance Scoring</span>
            <span className="badge badge-neutral">Cross-Chunk Contradiction Detector</span>
            <span className="badge badge-info">Missing Information Classifier</span>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 22 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: 'var(--accent-primary)' }}>
            <ShieldCheck size={20} />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>2. Claim Grounding Check</h3>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
            Decomposes generated answers into atomic factual claims. Matches each claim back to source chunk IDs to verify truthfulness. If an unsupported claim is found, triggers an automated <strong>Correction Loop</strong> (up to 2 retries).
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span className="badge badge-verified">Claim Extraction Engine</span>
            <span className="badge badge-warning">Automated Correction Loop</span>
            <span className="badge badge-info">Confidence Metric (0.0 - 1.0)</span>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 22 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: 'var(--accent-pink)' }}>
            <Sparkles size={20} />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>3. Transparent Fallback</h3>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
            When document evidence is missing or insufficient, the system transparently labels provenance and, if permitted in mode, falls back to Google Custom Search, clearly demarcating document facts from external facts.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span className="badge badge-neutral">Document Only Mode Enforcer</span>
            <span className="badge badge-info">Google Custom Search Adapter</span>
            <span className="badge badge-verified">External Fact Corroboration</span>
          </div>
        </div>
      </div>

      {/* Verification Matrix Table */}
      <div className="glass-panel" style={{ padding: 24 }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 14 }}>
          Verification Status Matrix
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.04)', textAlign: 'left' }}>
                <th style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>Status</th>
                <th style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>Criteria</th>
                <th style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>System Behavior</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span className="badge badge-verified">VERIFIED</span>
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  All key factual claims directly mapped to indexed chunks with high similarity.
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  Delivered with green verification shield and page citations.
                </td>
              </tr>
              <tr>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span className="badge badge-warning">NEEDS REVISION</span>
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  One or more claims cannot be substantiated from the retrieved passages.
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  Passes through correction prompt to eliminate ungrounded speculation.
                </td>
              </tr>
              <tr>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span className="badge badge-danger">CONFLICTING</span>
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  Uploaded documents present contradictory data on the queried topic.
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  Alerts the student to the conflicting sources and quotes each version.
                </td>
              </tr>
              <tr>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span className="badge badge-info">INSUFFICIENT</span>
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  No indexed passage reaches the similarity threshold (0.50).
                </td>
                <td style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)' }}>
                  Notifies student what is missing; activates web fallback if allowed.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
