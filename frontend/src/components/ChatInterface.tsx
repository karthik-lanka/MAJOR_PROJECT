import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, ShieldCheck, Globe, BookOpen, CheckCircle, ExternalLink, RefreshCw, Plus, Trash2, Sparkles, Paperclip, FileText, X, Lock } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ChatResponse,
  DocumentItem,
  sendChatMessage,
  uploadDocument,
  fetchDocumentStatus,
  fetchConversations,
  fetchConversationDetail,
  deleteConversation,
} from '../api/client';
import { InteractiveMcqList, parseMcqsFromMarkdown, McqItem } from './InteractiveMcqList';
import { UserProfile } from '../api/supabase';

export function cleanMathText(text: string): string {
  if (!text) return '';
  return text
    .replace(/\\log\b/g, 'log')
    .replace(/\\ln\b/g, 'ln')
    .replace(/\\times\b/g, '×')
    .replace(/\\le\b/g, '≤')
    .replace(/\\ge\b/g, '≥')
    .replace(/\\ne\b/g, '≠')
    .replace(/\\approx\b/g, '≈')
    .replace(/\\sqrt\{([^}]+)\}/g, '√($1)')
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '($1/$2)')
    .replace(/\\text\{([^}]+)\}/g, '$1')
    .replace(/\$\$([^$]+)\$\$/g, '$1')
    .replace(/\$([^$\n]+)\$/g, '$1')
    .replace(/\\([a-zA-Z]+)/g, '$1');
}

interface ChatInterfaceProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
  currentUser: UserProfile | null;
  onOpenAuth: () => void;
  onDocumentUploaded?: () => void;
}

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  responseMeta?: ChatResponse;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  documents,
  selectedDocIds,
  currentUser,
  onOpenAuth,
  onDocumentUploaded,
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [conversations, setConversations] = useState<Array<{ id: string; title: string; message_count: number }>>([]);
  const [selectedCitationSnippet, setSelectedCitationSnippet] = useState<any | null>(null);

  // Interactive Quiz state
  const [quizSelections, setQuizSelections] = useState<Record<string, string>>({});
  const [quizChecked, setQuizChecked] = useState<Record<string, boolean>>({});

  // Flashcards state
  const [flippedCards, setFlippedCards] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadConversations();
  }, [currentUser]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, uploadStatus]);

  const loadConversations = async () => {
    if (!currentUser) {
      setConversations([]);
      return;
    }
    try {
      const data = await fetchConversations(currentUser.email);
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const handleSelectConversation = async (id: string) => {
    try {
      setConversationId(id);
      const data = await fetchConversationDetail(id);
      if (data && data.messages) {
        const mapped: MessageItem[] = data.messages.map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          responseMeta: m.role === 'assistant' ? {
            answer: m.content,
            conversation_id: id,
            message_id: m.id,
            provenance: m.provenance || 'documents',
            citations: m.citations || [],
            intent: m.intent,
            response_format: m.response_format,
            structured_content: m.structured_content ? JSON.parse(m.structured_content) : null,
            web_fallback_used: m.provenance === 'web' || m.provenance === 'documents_web',
          } : undefined,
        }));
        setMessages(mapped);
      }
    } catch (err) {
      console.error('Failed to load conversation details:', err);
    }
  };

  const handleStartNewChat = () => {
    setConversationId(undefined);
    setMessages([]);
    setAttachedFile(null);
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      if (conversationId === id) {
        handleStartNewChat();
      }
      await loadConversations();
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
    }
  };

  const handleSendMessage = async (customPrompt?: string) => {
    const rawQuery = (customPrompt || inputQuestion).trim();
    if (!rawQuery && !attachedFile) return;
    if (isLoading) return;

    let query = rawQuery;
    let fileToUpload = attachedFile;
    setAttachedFile(null);

    const userMsgId = Date.now().toString();
    const promptDisplay = query || `Attached file: ${fileToUpload?.name}. Please analyze and provide comprehensive study insights.`;
    const newUserMsg: MessageItem = { id: userMsgId, role: 'user', content: promptDisplay };
    setMessages((prev) => [...prev, newUserMsg]);
    setInputQuestion('');
    setIsLoading(true);

    try {
      let activeDocIds = [...selectedDocIds];

      if (fileToUpload) {
        setUploadStatus(`Uploading ${fileToUpload.name}...`);
        try {
          const uploadedDoc = await uploadDocument(fileToUpload, currentUser ? currentUser.email : undefined);
          if (uploadedDoc?.id) {
            activeDocIds.push(uploadedDoc.id);
            setUploadStatus(`Indexing & analyzing ${fileToUpload.name}...`);

            // Poll until document is fully indexed and ready in vector store
            let isReady = false;
            let attempts = 0;
            while (!isReady && attempts < 35) {
              await new Promise((resolve) => setTimeout(resolve, 750));
              try {
                const statusRes = await fetchDocumentStatus(uploadedDoc.id);
                if (statusRes.processing_status === 'READY') {
                  isReady = true;
                  break;
                } else if (statusRes.processing_status === 'FAILED') {
                  throw new Error(statusRes.error_message || 'Document indexing failed');
                }
              } catch (pollErr: any) {
                if (pollErr.message && pollErr.message.includes('Document indexing failed')) {
                  throw pollErr;
                }
              }
              attempts++;
            }
          }
          if (onDocumentUploaded) {
            onDocumentUploaded();
          }
        } catch (uploadErr: any) {
          throw new Error(`File upload failed: ${uploadErr.message || 'Could not parse document'}`);
        } finally {
          setUploadStatus(null);
        }
      }

      const effectiveQuestion = query || `Please analyze the uploaded document "${fileToUpload?.name}", summarize key concepts, and prepare study review notes.`;

      const resp = await sendChatMessage({
        question: effectiveQuestion,
        document_ids: activeDocIds.length > 0 ? activeDocIds : undefined,
        conversation_id: conversationId,
        user_id: currentUser ? currentUser.email : undefined,
        mode: 'documents_web',
        enable_fact_check: true,
      });

      setConversationId(resp.conversation_id);
      const assistantMsg: MessageItem = {
        id: resp.message_id,
        role: 'assistant',
        content: resp.answer,
        responseMeta: resp,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      await loadConversations();
    } catch (err: any) {
      const errorMsg: MessageItem = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `**Error:** ${err.message || 'Failed to process question. Please try again.'}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setUploadStatus(null);
    }
  };

  const handleSelectQuizOption = (questionId: string, optionId: string) => {
    setQuizSelections((prev) => ({ ...prev, [questionId]: optionId }));
    setQuizChecked((prev) => ({ ...prev, [questionId]: true }));
  };

  const toggleFlipCard = (cardId: string) => {
    setFlippedCards((prev) => ({ ...prev, [cardId]: !prev[cardId] }));
  };

  return (
    <div style={{
      width: '100%',
      maxWidth: '100%',
      boxSizing: 'border-box',
      margin: '0 auto',
      padding: '16px 24px',
      display: 'flex',
      gap: 20,
      height: 'calc(100vh - 86px)',
    }}>
      {/* Sidebar: Conversations (ChatGPT styled light sidebar) */}
      <div style={{
        width: 280,
        display: 'flex',
        flexDirection: 'column',
        padding: '16px',
        flexShrink: 0,
        background: '#f9f9f9',
        border: '1px solid #e5e7eb',
        borderRadius: '16px',
      }}>
        <button
          onClick={handleStartNewChat}
          style={{
            width: '100%',
            marginBottom: 14,
            padding: '10px 14px',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '10px',
            color: '#0d0d0d',
            fontSize: '0.88rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            cursor: 'pointer',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = '#f3f4f6')}
          onMouseLeave={(e) => (e.currentTarget.style.background = '#ffffff')}
        >
          <Plus size={16} />
          <span>New Study Session</span>
        </button>

        {/* Saved Sessions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, padding: '0 4px' }}>
          <span style={{ fontSize: '0.76rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {currentUser ? 'My Conversations' : 'Study History'}
          </span>
          {currentUser && (
            <span style={{ fontSize: '0.72rem', color: '#0d0d0d', fontWeight: 500 }}>
              {currentUser.email.split('@')[0]}
            </span>
          )}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {!currentUser ? (
            <div style={{
              background: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: 16,
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 10,
              marginTop: 10,
            }}>
              <Lock size={20} color="#4b5563" />
              <p style={{ fontSize: '0.8rem', color: '#6b7280', margin: 0, lineHeight: 1.4 }}>
                Sign in or register to save your study sessions and chat history.
              </p>
              <button
                type="button"
                onClick={onOpenAuth}
                className="btn btn-primary"
                style={{ fontSize: '0.8rem', padding: '7px 14px', width: '100%', borderRadius: 8 }}
              >
                Sign In / Register
              </button>
            </div>
          ) : conversations.length === 0 ? (
            <p style={{ fontSize: '0.8rem', color: '#9ca3af', textAlign: 'center', marginTop: 24 }}>
              No saved conversations yet.
            </p>
          ) : (
            conversations.map((c) => {
              const isCurrent = c.id === conversationId;
              return (
                <div
                  key={c.id}
                  onClick={() => handleSelectConversation(c.id)}
                  style={{
                    padding: '9px 12px',
                    borderRadius: '8px',
                    background: isCurrent ? '#ececec' : 'transparent',
                    border: isCurrent ? '1px solid #d1d5db' : '1px solid transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.84rem',
                    color: isCurrent ? '#0d0d0d' : '#4b5563',
                    fontWeight: isCurrent ? 600 : 400,
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isCurrent) e.currentTarget.style.background = '#f0f0f0';
                  }}
                  onMouseLeave={(e) => {
                    if (!isCurrent) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 180 }}>
                    {c.title}
                  </span>
                  <button
                    onClick={(e) => handleDeleteConversation(e, c.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#9ca3af',
                      cursor: 'pointer',
                      padding: 2,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                    title="Delete session"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '16px',
        overflow: 'hidden',
      }}>
        {/* Messages Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
          {messages.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              textAlign: 'center',
              width: '100%',
              maxWidth: 1040,
              margin: '0 auto',
              padding: '24px 0',
            }}>
              <div style={{
                width: 52,
                height: 52,
                borderRadius: '50%',
                background: '#0d0d0d',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 18,
              }}>
                <Sparkles size={26} color="#ffffff" />
              </div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 8, color: '#0d0d0d' }}>
                AI Academic Study Assistant
              </h2>
              <p style={{ color: '#6b7280', fontSize: '0.92rem', marginBottom: 28, lineHeight: 1.5 }}>
                Ask questions about your uploaded textbooks, notes, and research papers. Answers are cross-verified against evidence, cited with page numbers, and adapted to your learning format.
              </p>

              {/* Quick Prompt Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, width: '100%' }}>
                {[
                  { text: 'Create 5 practice MCQs from my material', desc: 'Interactive quiz with instant grading' },
                  { text: 'Summarize the core concepts in a comparison table', desc: 'Structured tabular overview' },
                  { text: 'Explain the most complex theorem step by step', desc: 'Clear pedagogical breakdown' },
                  { text: 'Generate flashcards for definitions and formulas', desc: 'Interactive 3D flip study cards' },
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt.text)}
                    style={{
                      padding: '14px 16px',
                      textAlign: 'left',
                      cursor: 'pointer',
                      border: '1px solid #e5e7eb',
                      background: '#ffffff',
                      borderRadius: '12px',
                      transition: 'all 0.15s ease',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#f9fafb';
                      e.currentTarget.style.borderColor = '#d1d5db';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = '#ffffff';
                      e.currentTarget.style.borderColor = '#e5e7eb';
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '0.86rem', color: '#0d0d0d', marginBottom: 3 }}>
                      {prompt.text}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#6b7280' }}>
                      {prompt.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  gap: 12,
                  alignItems: 'flex-start',
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: msg.role === 'user' ? '80%' : '94%',
                }}
              >
                {msg.role === 'assistant' && (
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: '#0d0d0d',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: 2,
                  }}>
                    <Bot size={18} color="#ffffff" />
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
                  {/* Assistant Verification Bar */}
                  {msg.role === 'assistant' && msg.responseMeta && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                      {/* Provenance Badge */}
                      {msg.responseMeta.provenance === 'documents' && (
                        <span className="badge badge-verified">
                          <CheckCircle size={12} /> Grounded in Document Evidence
                        </span>
                      )}
                      {msg.responseMeta.provenance === 'documents_web' && (
                        <span className="badge badge-info">
                          <Globe size={12} /> Augmented with Web Search
                        </span>
                      )}
                      {msg.responseMeta.provenance === 'web' && (
                        <span className="badge badge-warning">
                          <Globe size={12} /> Web Evidence
                        </span>
                      )}

                      {/* Answer Verification */}
                      {msg.responseMeta.answer_verification && (
                        <span className={`badge ${msg.responseMeta.answer_verification.status === 'VERIFIED' ? 'badge-verified' : 'badge-warning'}`}>
                          <ShieldCheck size={12} /> {msg.responseMeta.answer_verification.status}
                          {msg.responseMeta.answer_verification.overall_confidence && ` (${Math.round(msg.responseMeta.answer_verification.overall_confidence * 100)}%)`}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div
                    style={{
                      padding: msg.role === 'user' ? '12px 18px' : '6px 0',
                      borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '0',
                      background: msg.role === 'user' ? '#f4f4f4' : 'transparent',
                      border: msg.role === 'user' ? '1px solid #e5e5e5' : 'none',
                      color: '#0d0d0d',
                    }}
                  >
                    {(() => {
                      let mcqs: McqItem[] = [];
                      let remainingText = msg.content || '';

                      if (msg.responseMeta?.structured_content && Array.isArray(msg.responseMeta.structured_content) && msg.responseMeta.structured_content[0]?.options) {
                        mcqs = msg.responseMeta.structured_content;
                        const parsed = parseMcqsFromMarkdown(remainingText);
                        remainingText = parsed.remainingText;
                      } else if (msg.role === 'assistant') {
                        const parsed = parseMcqsFromMarkdown(remainingText);
                        if (parsed.mcqs.length > 0) {
                          mcqs = parsed.mcqs;
                          remainingText = parsed.remainingText;
                        }
                      }

                      return (
                        <>
                          {remainingText.trim() && (
                            <div className="markdown-content">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {cleanMathText(remainingText)}
                              </ReactMarkdown>
                            </div>
                          )}

                          {mcqs.length > 0 && (
                            <div style={{ marginTop: remainingText.trim() ? 16 : 4 }}>
                              <InteractiveMcqList questions={mcqs} />
                            </div>
                          )}
                        </>
                      );
                    })()}

                    {/* Interactive Flashcards Component */}
                    {msg.responseMeta?.structured_content && Array.isArray(msg.responseMeta.structured_content) && msg.responseMeta.structured_content[0]?.front && (
                      <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0d0d0d' }}>
                          Interactive Revision Flashcards (Click to flip)
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                          {msg.responseMeta.structured_content.map((card: any, cIdx: number) => {
                            const isFlipped = flippedCards[`${msg.id}_${cIdx}`];
                            return (
                              <div
                                key={cIdx}
                                onClick={() => toggleFlipCard(`${msg.id}_${cIdx}`)}
                                style={{
                                  height: 150,
                                  background: isFlipped ? '#f3f4f6' : '#ffffff',
                                  border: `1px solid ${isFlipped ? '#0d0d0d' : '#e5e7eb'}`,
                                  borderRadius: '12px',
                                  padding: 16,
                                  display: 'flex',
                                  flexDirection: 'column',
                                  justifyContent: 'space-between',
                                  cursor: 'pointer',
                                  transition: 'all 0.2s ease',
                                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                                }}
                              >
                                <span className="badge badge-neutral" style={{ alignSelf: 'flex-start', fontSize: '0.68rem' }}>
                                  {isFlipped ? 'Answer / Definition' : 'Prompt / Concept'}
                                </span>
                                <div style={{ textAlign: 'center', fontSize: '0.9rem', fontWeight: 600, color: '#0d0d0d' }}>
                                  {isFlipped ? card.back : card.front}
                                </div>
                                <span style={{ fontSize: '0.72rem', color: '#6b7280', textAlign: 'right' }}>
                                  Click to flip ↻
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Citations Bar */}
                    {msg.responseMeta?.citations && msg.responseMeta.citations.length > 0 && (
                      <div style={{ marginTop: 14, borderTop: '1px solid #e5e7eb', paddingTop: 10 }}>
                        <div style={{ fontSize: '0.74rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <BookOpen size={12} /> Verified Citations & References ({msg.responseMeta.citations.length})
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {msg.responseMeta.citations.map((c, cIdx) => (
                            <button
                              key={cIdx}
                              onClick={() => setSelectedCitationSnippet(c)}
                              style={{
                                padding: '4px 9px',
                                fontSize: '0.76rem',
                                borderRadius: '6px',
                                background: '#f9fafb',
                                border: '1px solid #e5e7eb',
                                color: '#374151',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 4,
                              }}
                            >
                              {c.source_type === 'document' ? (
                                <>
                                  <span>{c.filename || 'Document'}</span>
                                  {c.page_number && <span style={{ color: '#0284c7', fontWeight: 600 }}>p.{c.page_number}</span>}
                                </>
                              ) : (
                                <>
                                  <Globe size={11} />
                                  <span>{c.title ? c.title.slice(0, 22) + '...' : 'Web'}</span>
                                </>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    background: '#f3f4f6',
                    border: '1px solid #e5e7eb',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: 2,
                  }}>
                    <User size={16} color="#374151" />
                  </div>
                )}
              </div>
            ))
          )}

          {isLoading && (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                background: '#0d0d0d',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <RefreshCw size={16} className="animate-spin" color="#ffffff" />
              </div>
              <div style={{
                padding: '10px 16px',
                borderRadius: '10px',
                background: '#f9fafb',
                border: '1px solid #e5e7eb',
                fontSize: '0.86rem',
                color: '#4b5563',
              }}>
                Searching study materials, verifying evidence, and generating response...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar (ChatGPT Floating Style) */}
        <div style={{ padding: '16px 24px 20px', borderTop: '1px solid #f3f4f6' }}>
          {attachedFile && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '6px 12px',
              marginBottom: 8,
              fontSize: '0.82rem',
              color: '#374151',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileText size={14} color="#0d0d0d" />
                <span style={{ fontWeight: 500 }}>{attachedFile.name}</span>
                <span style={{ color: '#9ca3af' }}>({(attachedFile.size / 1024).toFixed(1)} KB)</span>
              </div>
              <button
                type="button"
                onClick={() => setAttachedFile(null)}
                style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', padding: 0 }}
              >
                <X size={14} />
              </button>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: '24px',
              padding: '6px 10px 6px 16px',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
              transition: 'border-color 0.15s ease',
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
            />

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: attachedFile ? '#0d0d0d' : '#6b7280',
                display: 'flex',
                alignItems: 'center',
                padding: '4px',
              }}
              title="Attach study document or image"
            >
              <Paperclip size={18} />
            </button>

            <input
              type="text"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder={attachedFile ? `Ask a question about ${attachedFile.name}...` : "Ask a question, request MCQs, summarize a concept, or quiz yourself..."}
              disabled={isLoading}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                color: '#0d0d0d',
                fontSize: '0.92rem',
                outline: 'none',
              }}
            />

            <button
              type="submit"
              disabled={(!inputQuestion.trim() && !attachedFile) || isLoading}
              style={{
                width: 34,
                height: 34,
                borderRadius: '50%',
                background: (!inputQuestion.trim() && !attachedFile) || isLoading ? '#f3f4f6' : '#0d0d0d',
                color: (!inputQuestion.trim() && !attachedFile) || isLoading ? '#9ca3af' : '#ffffff',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: (!inputQuestion.trim() && !attachedFile) || isLoading ? 'default' : 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      </div>

      {/* Citation Snippet Inspector Modal */}
      {selectedCitationSnippet && (
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
            maxWidth: 580,
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '16px',
            padding: 24,
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <BookOpen size={18} color="#0d0d0d" />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#0d0d0d', margin: 0 }}>
                  Citation Evidence
                </h3>
              </div>
              <button
                onClick={() => setSelectedCitationSnippet(null)}
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: '0.8rem' }}
              >
                Close
              </button>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <span className="badge badge-info">{selectedCitationSnippet.source_type}</span>
              {selectedCitationSnippet.filename && (
                <span className="badge badge-neutral">{selectedCitationSnippet.filename}</span>
              )}
              {selectedCitationSnippet.page_number && (
                <span className="badge badge-neutral">Page {selectedCitationSnippet.page_number}</span>
              )}
              {selectedCitationSnippet.relevance_score && (
                <span className="badge badge-verified">Score: {selectedCitationSnippet.relevance_score.toFixed(3)}</span>
              )}
            </div>

            {selectedCitationSnippet.url && (
              <a
                href={selectedCitationSnippet.url}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#0284c7', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 12 }}
              >
                {selectedCitationSnippet.url} <ExternalLink size={12} />
              </a>
            )}

            <div style={{ background: '#f9fafb', padding: 14, borderRadius: '8px', border: '1px solid #e5e7eb', maxHeight: 280, overflowY: 'auto' }}>
              <p style={{ fontSize: '0.88rem', color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap', margin: 0 }}>
                {selectedCitationSnippet.snippet || 'No excerpt available.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
