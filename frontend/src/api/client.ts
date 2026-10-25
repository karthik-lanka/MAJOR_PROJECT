/**
 * API Client for AI-Powered Multimodal Study Assistant
 */

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  services: Record<string, any>;
}

export interface StatusResponse {
  gemini_configured: boolean;
  gemini_model: string;
  embedding_model: string;
  embedding_dimension: number;
  pinecone_configured: boolean;
  pinecone_index: string;
  web_search_configured: boolean;
  total_documents: number;
  total_chunks: number;
  total_conversations: number;
}

export interface DocumentItem {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  upload_timestamp: string;
  processing_status: 'UPLOADED' | 'EXTRACTING' | 'CHUNKING' | 'EMBEDDING' | 'INDEXING' | 'READY' | 'FAILED' | 'DELETING';
  page_count?: number;
  chunk_count: number;
  error_message?: string;
}

export interface ChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  chunk_text: string;
  page_number?: number;
  section_heading?: string;
  token_count?: number;
}

export interface CitationItem {
  source_type: 'document' | 'web';
  document_id?: string;
  chunk_id?: string;
  filename?: string;
  page_number?: number;
  snippet?: string;
  url?: string;
  title?: string;
  relevance_score?: number;
}

export interface ClaimVerificationItem {
  claim: string;
  verdict: 'SUPPORTED' | 'CONTRADICTED' | 'NOT_ENOUGH_EVIDENCE';
  source_ids: string[];
  explanation?: string;
}

export interface ContextVerificationItem {
  status: 'SUFFICIENT' | 'PARTIALLY_SUFFICIENT' | 'INSUFFICIENT' | 'CONFLICTING';
  relevance: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  missing_information: string[];
  conflicts_detected: boolean;
  conflict_details?: string;
  supporting_chunk_ids: string[];
  reason: string;
}

export interface AnswerVerificationItem {
  status: 'VERIFIED' | 'NEEDS_REVISION' | 'UNVERIFIABLE';
  claims: ClaimVerificationItem[];
  unsupported_claims: string[];
  overall_confidence?: number;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  message_id: string;
  provenance: string;
  citations: CitationItem[];
  context_verification?: ContextVerificationItem;
  answer_verification?: AnswerVerificationItem;
  web_fallback_used: boolean;
  intent?: string;
  response_format?: string;
  structured_content?: any;
  processing_time_ms?: number;
  error?: string;
}

export interface StudyResponse {
  content_type: string;
  title: string;
  content: string;
  structured_content?: any;
  citations: Array<{ document_id?: string; filename?: string; page_number?: number; snippet?: string }>;
  document_ids: string[];
  processing_time_ms?: number;
  error?: string;
}

const API_BASE = '';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error('Status check failed');
  return res.json();
}

export async function fetchDocuments(userId?: string): Promise<{ documents: DocumentItem[]; total: number }> {
  const url = userId
    ? `${API_BASE}/api/documents?user_id=${encodeURIComponent(userId)}`
    : `${API_BASE}/api/documents`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentDetail(id: string): Promise<{ document: DocumentItem; chunks: ChunkItem[]; total_chunks: number }> {
  const res = await fetch(`${API_BASE}/api/documents/${id}`);
  if (!res.ok) throw new Error('Failed to fetch document details');
  return res.json();
}

export async function fetchDocumentStatus(id: string): Promise<{
  id: string;
  filename: string;
  processing_status: string;
  page_count: number;
  chunk_count: number;
  error_message?: string;
}> {
  const res = await fetch(`${API_BASE}/api/documents/${id}/status`);
  if (!res.ok) throw new Error('Failed to fetch document status');
  return res.json();
}

export async function uploadDocument(file: File, userId?: string): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);
  if (userId) {
    formData.append('user_id', userId);
  }
  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function reprocessDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/documents/${id}/reprocess`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reprocess document');
}

export async function sendChatMessage(data: {
  question: string;
  document_ids?: string[];
  conversation_id?: string;
  user_id?: string;
  mode?: 'documents_only' | 'documents_web';
  enable_fact_check?: boolean;
}): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to process question' }));
    throw new Error(err.detail || 'Failed to process question');
  }
  return res.json();
}

export async function fetchConversations(userId?: string): Promise<{ conversations: Array<{ id: string; title: string; created_at: string; updated_at: string; message_count: number }> }> {
  if (!userId) {
    return { conversations: [] };
  }
  const res = await fetch(`${API_BASE}/api/conversations?user_id=${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error('Failed to fetch conversations');
  return res.json();
}

export async function fetchConversationDetail(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`);
  if (!res.ok) throw new Error('Failed to fetch conversation');
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete conversation');
}

export async function generateSummary(data: {
  document_ids: string[];
  detail_level?: 'brief' | 'standard' | 'detailed';
  section?: string;
  topic?: string;
  max_length?: number;
}): Promise<StudyResponse> {
  const res = await fetch(`${API_BASE}/api/study/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to generate summary');
  return res.json();
}

export async function explainConcept(data: {
  concept: string;
  document_ids?: string[];
  level?: 'simple' | 'standard' | 'advanced';
  include_examples?: boolean;
}): Promise<StudyResponse> {
  const res = await fetch(`${API_BASE}/api/study/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to explain concept');
  return res.json();
}

export async function generateRevisionNotes(data: {
  document_ids: string[];
  topics?: string[];
  format?: 'bullet_points' | 'detailed' | 'exam_ready' | 'flashcards';
}): Promise<StudyResponse> {
  const res = await fetch(`${API_BASE}/api/study/revision-notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to generate revision notes');
  return res.json();
}

export async function generatePracticeQuestions(data: {
  document_ids: string[];
  question_type?: 'mcq' | 'short_answer' | 'long_answer' | 'true_false' | 'fill_blanks' | 'mixed';
  count?: number;
  difficulty?: 'easy' | 'medium' | 'hard' | 'mixed';
  topics?: string[];
}): Promise<StudyResponse> {
  const res = await fetch(`${API_BASE}/api/study/practice-questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to generate practice questions');
  return res.json();
}
