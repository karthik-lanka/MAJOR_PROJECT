import React, { useState, useRef } from 'react';
import { UploadCloud, File, Trash2, RefreshCw, AlertCircle, CheckCircle, Clock, Layers, X, Lock } from 'lucide-react';
import { DocumentItem, ChunkItem, uploadDocument, deleteDocument, reprocessDocument, fetchDocumentDetail } from '../api/client';
import { UserProfile } from '../api/supabase';

interface DocumentManagerProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
  currentUser?: UserProfile | null;
  onOpenAuth?: () => void;
  onToggleSelectDoc: (id: string) => void;
  onRefreshDocs: () => Promise<void>;
}

export const DocumentManager: React.FC<DocumentManagerProps> = ({
  documents,
  selectedDocIds,
  currentUser,
  onOpenAuth,
  onToggleSelectDoc,
  onRefreshDocs,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [activeChunksModal, setActiveChunksModal] = useState<{
    doc: DocumentItem;
    chunks: ChunkItem[];
  } | null>(null);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadError(null);

    try {
      for (let i = 0; i < files.length; i++) {
        await uploadDocument(files[i], currentUser?.email);
      }
      await onRefreshDocs();
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"? This removes all vector chunks.`)) return;
    try {
      await deleteDocument(id);
      await onRefreshDocs();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleReprocess = async (id: string) => {
    try {
      await reprocessDocument(id);
      await onRefreshDocs();
    } catch (err: any) {
      alert(`Reprocess failed: ${err.message}`);
    }
  };

  const handleViewChunks = async (doc: DocumentItem) => {
    setLoadingChunks(true);
    try {
      const data = await fetchDocumentDetail(doc.id);
      setActiveChunksModal({ doc: data.document, chunks: data.chunks });
    } catch (err: any) {
      alert(`Failed to load chunks: ${err.message}`);
    } finally {
      setLoadingChunks(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'READY':
        return <span className="badge badge-verified"><CheckCircle size={12} /> Ready</span>;
      case 'FAILED':
        return <span className="badge badge-danger"><AlertCircle size={12} /> Failed</span>;
      case 'EXTRACTING':
      case 'CHUNKING':
      case 'EMBEDDING':
      case 'INDEXING':
        return <span className="badge badge-info"><RefreshCw size={12} className="animate-spin" /> {status}</span>;
      default:
        return <span className="badge badge-neutral"><Clock size={12} /> {status}</span>;
    }
  };

  return (
    <div style={{ maxWidth: 1600, width: '100%', margin: '20px auto', padding: '0 24px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header and Upload Dropzone */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '16px',
        padding: '28px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: 6, color: '#0d0d0d' }}>
              Document Ingestion & Multi-modal Indexing
            </h2>
            <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>
              Upload academic materials (PDFs, DOCX, TXT, scanned images). Text is automatically parsed, normalized, chunked, and indexed for semantic search.
            </p>
          </div>
          <button
            onClick={() => onRefreshDocs()}
            className="btn btn-secondary"
            style={{ fontSize: '0.85rem' }}
          >
            <RefreshCw size={14} /> Refresh Documents
          </button>
        </div>

        {/* Drag and drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFileUpload(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? '#0d0d0d' : '#d1d5db'}`,
            borderRadius: '12px',
            padding: '36px 20px',
            textAlign: 'center',
            background: isDragging ? '#f3f4f6' : '#f9fafb',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            multiple
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
          <div style={{
            width: 50,
            height: 50,
            borderRadius: '50%',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            color: '#0d0d0d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}>
            <UploadCloud size={24} />
          </div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: 4, color: '#0d0d0d' }}>
            {isUploading ? 'Uploading and parsing document...' : 'Click or Drag academic files here'}
          </h3>
          <p style={{ fontSize: '0.84rem', color: '#6b7280', marginBottom: 12 }}>
            Supports PDF (text & scanned OCR), DOCX, Plain Text, and Images (PNG/JPG) up to 25 MB
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span className="badge badge-neutral">.PDF (PyMuPDF)</span>
            <span className="badge badge-neutral">.DOCX (Word)</span>
            <span className="badge badge-neutral">.TXT</span>
            <span className="badge badge-neutral">OCR (Vision Engine)</span>
          </div>
        </div>

        {uploadError && (
          <div style={{ marginTop: 16, padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertCircle size={18} />
            <span style={{ fontSize: '0.88rem' }}>{uploadError}</span>
          </div>
        )}
      </div>

      {/* Document Library List */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#0d0d0d' }}>
            Indexed Academic Materials ({documents.length})
          </h3>
          <span style={{ fontSize: '0.84rem', color: '#6b7280' }}>
            Selected for context: {selectedDocIds.length === 0 ? 'All Documents' : `${selectedDocIds.length} document(s)`}
          </span>
        </div>

        {documents.length === 0 ? (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: '#6b7280' }}>
            <File size={40} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
            <p style={{ margin: '0 0 12px 0' }}>
              {currentUser
                ? `No documents uploaded yet for ${currentUser.email}. Upload notes or slides above to begin.`
                : 'No documents uploaded yet. Upload course materials above to begin.'}
            </p>
            {!currentUser && onOpenAuth && (
              <button
                type="button"
                onClick={onOpenAuth}
                className="btn btn-primary"
                style={{ padding: '8px 20px', fontSize: '0.85rem' }}
              >
                Sign In / Register
              </button>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {documents.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  style={{
                    padding: '14px 18px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 16,
                    background: isSelected ? '#f9fafb' : '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderLeft: isSelected ? '4px solid #0d0d0d' : '1px solid #e5e7eb',
                    borderRadius: '12px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14, flex: 1, minWidth: 260 }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelectDoc(doc.id)}
                      style={{ width: 17, height: 17, accentColor: '#0d0d0d', cursor: 'pointer' }}
                      title="Select for Q&A search context"
                    />
                    <div style={{
                      width: 38,
                      height: 38,
                      borderRadius: '8px',
                      background: '#f3f4f6',
                      border: '1px solid #e5e7eb',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#0d0d0d',
                    }}>
                      <File size={18} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#0d0d0d', marginBottom: 2 }}>
                        {doc.original_filename || doc.filename}
                      </h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.78rem', color: '#6b7280' }}>
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span>{doc.page_count ? `${doc.page_count} pages` : 'N/A'}</span>
                        <span>•</span>
                        <span>{doc.chunk_count} chunks</span>
                        <span>•</span>
                        <span>{new Date(doc.upload_timestamp).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {getStatusBadge(doc.processing_status)}

                    <button
                      onClick={() => handleViewChunks(doc)}
                      className="btn btn-secondary"
                      style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                      title="Inspect extracted chunks"
                    >
                      <Layers size={13} /> Chunks
                    </button>

                    <button
                      onClick={() => handleReprocess(doc.id)}
                      className="btn btn-secondary"
                      style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                      title="Re-run extraction, chunking and indexing"
                    >
                      <RefreshCw size={13} /> Reprocess
                    </button>

                    <button
                      onClick={() => handleDelete(doc.id, doc.original_filename)}
                      className="btn btn-secondary"
                      style={{ padding: '6px 10px', fontSize: '0.8rem', color: '#dc2626' }}
                      title="Delete document and chunks"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Chunks Inspection Modal */}
      {activeChunksModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.45)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: 20,
        }}>
          <div style={{
            width: '100%',
            maxWidth: 820,
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '16px',
            padding: 24,
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '1px solid #e5e7eb', paddingBottom: 14 }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0d0d0d', margin: 0 }}>
                  Chunks for {activeChunksModal.doc.original_filename}
                </h3>
                <p style={{ fontSize: '0.82rem', color: '#6b7280', margin: '4px 0 0 0' }}>
                  Total {activeChunksModal.chunks.length} semantically partitioned chunks in vector index
                </p>
              </div>
              <button
                onClick={() => setActiveChunksModal(null)}
                style={{
                  background: '#f3f4f6',
                  border: 'none',
                  borderRadius: '50%',
                  width: 30,
                  height: 30,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#6b7280',
                  cursor: 'pointer',
                }}
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingRight: 6 }}>
              {activeChunksModal.chunks.map((chunk) => (
                <div key={chunk.id} style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '10px', padding: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="badge badge-info">Chunk #{chunk.chunk_index}</span>
                      {chunk.page_number && <span className="badge badge-neutral">Page {chunk.page_number}</span>}
                      {chunk.section_heading && <span style={{ fontSize: '0.8rem', color: '#0284c7', fontWeight: 600 }}>{chunk.section_heading}</span>}
                    </div>
                    <span style={{ fontSize: '0.74rem', color: '#6b7280' }}>~{chunk.token_count || 0} tokens</span>
                  </div>
                  <p style={{ fontSize: '0.86rem', color: '#1f2937', whiteSpace: 'pre-wrap', lineHeight: 1.6, margin: 0 }}>
                    {chunk.chunk_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
