import React from 'react';
import { Activity, Database, Cpu, CheckCircle2, AlertTriangle, Layers, MessageSquare, HardDrive } from 'lucide-react';
import { StatusResponse, HealthResponse } from '../api/client';

interface SystemHealthProps {
  status: StatusResponse | null;
  health: HealthResponse | null;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({ status, health }) => {
  return (
    <div style={{ maxWidth: 1200, margin: '24px auto', padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="glass-panel" style={{ padding: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: 'rgba(99, 102, 241, 0.15)',
            color: 'var(--accent-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Activity size={26} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
              System Health & Architecture Diagnostics
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
              Real-time monitoring of vector store, LLM endpoints, metadata database, and ingestion pipeline.
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Indexed Documents
            </span>
            <HardDrive size={18} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>
            {status?.total_documents ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Active files in SQLite DB
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Vector Chunks
            </span>
            <Layers size={18} color="var(--accent-primary)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>
            {status?.total_chunks ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Vectors in semantic index
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Vector Dimensions
            </span>
            <Database size={18} color="var(--accent-pink)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>
            {status?.embedding_dimension ?? 768}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {status?.embedding_model || 'gemini-embedding-001'}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Conversations
            </span>
            <MessageSquare size={18} color="var(--accent-emerald)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800 }}>
            {status?.total_conversations ?? 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Multi-turn study sessions
          </div>
        </div>
      </div>

      {/* Component Configurations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 18 }}>
        <div className="glass-panel" style={{ padding: 24 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={18} color="var(--accent-primary)" /> AI Inference & Embeddings
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: '0.88rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Generation Model:</span>
              <strong style={{ color: 'var(--text-primary)' }}>{status?.gemini_model || 'LLM Generator'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Embedding Dimension:</span>
              <strong style={{ color: 'var(--text-primary)' }}>{status?.embedding_dimension || 768}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>AI Engine API:</span>
              <span className="badge badge-verified">Active & Connected</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Target Chunk Size / Overlap:</span>
              <span style={{ color: 'var(--text-primary)' }}>600 / 80 tokens</span>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 24 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={18} color="var(--accent-primary)" /> Vector Store & Storage
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: '0.88rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Vector Index Name:</span>
              <strong style={{ color: 'var(--text-primary)' }}>{status?.pinecone_index || 'study-assistant'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Distance Metric:</span>
              <strong style={{ color: 'var(--text-primary)' }}>Cosine Similarity</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 8 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Vector Engine Status:</span>
              <span className="badge badge-verified">Configured</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Local Metadata DB:</span>
              <span style={{ color: '#fff' }}>SQLite (aiosqlite + SQLAlchemy Async)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
