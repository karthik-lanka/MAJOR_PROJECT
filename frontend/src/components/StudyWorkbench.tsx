import React, { useState } from 'react';
import { BookOpen, Copy, Check, ArrowRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  DocumentItem,
  StudyResponse,
  generateSummary,
  explainConcept,
  generateRevisionNotes,
  generatePracticeQuestions,
} from '../api/client';
import { InteractiveMcqList, parseMcqsFromMarkdown, McqItem } from './InteractiveMcqList';

interface StudyWorkbenchProps {
  documents: DocumentItem[];
  selectedDocIds: string[];
}

export const StudyWorkbench: React.FC<StudyWorkbenchProps> = ({
  documents,
  selectedDocIds,
}) => {
  const [activeTool, setActiveTool] = useState<'summarize' | 'explain' | 'revision' | 'practice'>('summarize');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<StudyResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form states
  const [detailLevel, setDetailLevel] = useState<'brief' | 'standard' | 'detailed'>('standard');
  const [summaryTopic, setSummaryTopic] = useState('');
  const [concept, setConcept] = useState('');
  const [explainLevel, setExplainLevel] = useState<'simple' | 'standard' | 'advanced'>('standard');
  const [includeExamples, setIncludeExamples] = useState(true);
  const [notesFormat, setNotesFormat] = useState<'bullet_points' | 'detailed' | 'exam_ready' | 'flashcards'>('exam_ready');
  const [topicsInput, setTopicsInput] = useState('');
  const [practiceTopic, setPracticeTopic] = useState('');
  const [questionType, setQuestionType] = useState<'mcq' | 'short_answer' | 'mixed'>('mixed');
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard' | 'mixed'>('medium');

  // Effective document IDs (selected or first available)
  const effectiveDocIds = selectedDocIds.length > 0
    ? selectedDocIds
    : documents.map((d) => d.id);

  // Parse questions count from user prompt (defaults to 10 if user doesn't specify)
  const parsePracticeCount = (text: string): { count: number; cleanTopic: string } => {
    let count = 10;
    const match = text.match(/\b(\d+)\s*(?:questions?|mcqs?|items?|problems?)?\b/i);
    if (match) {
      const parsed = parseInt(match[1], 10);
      if (parsed > 0 && parsed <= 50) {
        count = parsed;
      }
    }
    const cleanTopic = text
      .replace(/\b(?:give\s+me\s+)?\d+\s*(?:questions?|mcqs?|items?|problems?)\s*(?:on|about|of)?\b/gi, '')
      .trim();
    return { count, cleanTopic };
  };

  const handleRunTool = async () => {
    setFormError(null);

    if (effectiveDocIds.length === 0) {
      setFormError('Please upload or select at least one document first.');
      return;
    }

    if (activeTool === 'explain' && !concept.trim()) {
      setFormError('Please enter a concept or topic name to explain.');
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      let resp: StudyResponse;
      if (activeTool === 'summarize') {
        resp = await generateSummary({
          document_ids: effectiveDocIds,
          detail_level: detailLevel,
          topic: summaryTopic.trim() || undefined,
        });
      } else if (activeTool === 'explain') {
        resp = await explainConcept({
          concept: concept.trim(),
          document_ids: effectiveDocIds,
          level: explainLevel,
          include_examples: includeExamples,
        });
      } else if (activeTool === 'revision') {
        const topics = topicsInput.split(',').map((t) => t.trim()).filter(Boolean);
        resp = await generateRevisionNotes({
          document_ids: effectiveDocIds,
          format: notesFormat,
          topics,
        });
      } else {
        const { count, cleanTopic } = parsePracticeCount(practiceTopic);
        const topics = cleanTopic ? [cleanTopic] : (practiceTopic.trim() ? [practiceTopic.trim()] : []);
        resp = await generatePracticeQuestions({
          document_ids: effectiveDocIds,
          question_type: questionType,
          count,
          difficulty,
          topics,
        });
      }
      setResult(resp);
    } catch (err: any) {
      setFormError(err.message || 'Error generating study material. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (!result) return;
    navigator.clipboard.writeText(result.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ maxWidth: 1600, width: '100%', margin: '20px auto', padding: '0 24px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Tool Header & Selector */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: 6, color: '#0d0d0d' }}>
          AI Study & Exam Preparation Workbench
        </h2>
        <p style={{ color: '#6b7280', fontSize: '0.88rem', marginBottom: 20 }}>
          Generate focused academic aids grounded directly in your syllabus and uploaded materials.
        </p>

        {/* Tab options */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { id: 'summarize', label: 'Summarize Material', desc: 'Brief, standard, or deep executive summary' },
            { id: 'explain', label: 'Concept Deep-Dive', desc: 'Analogies, mathematical logic & intuition' },
            { id: 'revision', label: 'Revision Notes', desc: 'Exam-ready formulas, theorems & checklists' },
            { id: 'practice', label: 'Practice Questions', desc: 'MCQs, short answer & examination problems' },
          ].map((t) => {
            const isActive = activeTool === t.id;
            return (
              <button
                key={t.id}
                onClick={() => {
                  setActiveTool(t.id as any);
                  setFormError(null);
                }}
                style={{
                  padding: '14px 16px',
                  borderRadius: '12px',
                  background: isActive ? '#f9fafb' : '#ffffff',
                  border: `1px solid ${isActive ? '#0d0d0d' : '#e5e7eb'}`,
                  color: '#0d0d0d',
                  cursor: 'pointer',
                  textAlign: 'left',
                  boxShadow: isActive ? '0 1px 3px rgba(0,0,0,0.05)' : 'none',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.92rem', marginBottom: 4, color: '#0d0d0d' }}>
                  {t.label}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#6b7280' }}>
                  {t.desc}
                </div>
              </button>
            );
          })}
        </div>

        {/* Dynamic Controls based on tool */}
        <div style={{
          background: '#f9fafb',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}>
          {activeTool === 'summarize' && (
            <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 280 }}>
                <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Concept or Topic Name (Optional - leave blank to summarize all material)
                </label>
                <input
                  type="text"
                  value={summaryTopic}
                  onChange={(e) => setSummaryTopic(e.target.value)}
                  placeholder="e.g. Cache Memory, Pipelining, Gradient Descent, Relational Algebra"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    color: '#0d0d0d',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.88rem',
                  }}
                />
              </div>
              <div style={{ minWidth: 220 }}>
                <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Detail Level
                </label>
                <select
                  value={detailLevel}
                  onChange={(e) => setDetailLevel(e.target.value as any)}
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    color: '#0d0d0d',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.88rem',
                  }}
                >
                  <option value="brief">Brief (Key bullet points)</option>
                  <option value="standard">Standard (Comprehensive overview)</option>
                  <option value="detailed">Detailed (Deep section-by-section breakdown)</option>
                </select>
              </div>
            </div>
          )}

          {activeTool === 'explain' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Concept or Topic Name
                </label>
                <input
                  type="text"
                  value={concept}
                  onChange={(e) => setConcept(e.target.value)}
                  placeholder="e.g. Backpropagation in Neural Networks, Relational Algebra, Dijkstra's Algorithm"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    color: '#0d0d0d',
                    padding: '9px 14px',
                    borderRadius: '8px',
                    fontSize: '0.88rem',
                  }}
                />
              </div>
              <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                    Pedagogical Level
                  </label>
                  <select
                    value={explainLevel}
                    onChange={(e) => setExplainLevel(e.target.value as any)}
                    style={{
                      background: '#ffffff',
                      border: '1px solid #d1d5db',
                      color: '#0d0d0d',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '0.88rem',
                    }}
                  >
                    <option value="simple">Simple (Intuitive ELI5 style)</option>
                    <option value="standard">Standard (Undergraduate level)</option>
                    <option value="advanced">Advanced (Mathematical rigour & edge cases)</option>
                  </select>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', cursor: 'pointer', marginTop: 20, color: '#374151' }}>
                  <input
                    type="checkbox"
                    checked={includeExamples}
                    onChange={(e) => setIncludeExamples(e.target.checked)}
                    style={{ accentColor: '#0d0d0d' }}
                  />
                  <span>Include worked examples & code snippets</span>
                </label>
              </div>
            </div>
          )}

          {activeTool === 'revision' && (
            <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div>
                <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Format
                </label>
                <select
                  value={notesFormat}
                  onChange={(e) => setNotesFormat(e.target.value as any)}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    color: '#0d0d0d',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.88rem',
                  }}
                >
                  <option value="exam_ready">Exam Ready (Formulas + Pitfalls + Highlights)</option>
                  <option value="bullet_points">Concise Bullet Points</option>
                  <option value="detailed">Detailed Study Guide</option>
                  <option value="flashcards">Flashcard Summary Table</option>
                </select>
              </div>
              <div style={{ flex: 1, minWidth: 260 }}>
                <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Optional Specific Focus Topics (comma separated)
                </label>
                <input
                  type="text"
                  value={topicsInput}
                  onChange={(e) => setTopicsInput(e.target.value)}
                  placeholder="e.g. Pipelining, Cache Coherence, Memory Hierarchy"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    color: '#0d0d0d',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.88rem',
                  }}
                />
              </div>
            </div>
          )}

          {activeTool === 'practice' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                  Concept or Topic Name / Focus Area
                </label>
                <input
                  type="text"
                  value={practiceTopic}
                  onChange={(e) => setPracticeTopic(e.target.value)}
                  placeholder="e.g. 5 questions on Binary Trees, or Operating Systems (defaults to 10 questions)"
                  style={{
                    width: '100%',
                    background: '#ffffff',
                    border: '1px solid #d1d5db',
                    color: '#0d0d0d',
                    padding: '9px 14px',
                    borderRadius: '8px',
                    fontSize: '0.88rem',
                  }}
                />
                <span style={{ fontSize: '0.78rem', color: '#6b7280', marginTop: 4, display: 'block' }}>
                  Tip: Specify the number of questions in your text (e.g. &quot;5 questions on sorting&quot;). If no number is mentioned, 10 questions are generated.
                </span>
              </div>
              <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                    Question Type
                  </label>
                  <select
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value as any)}
                    style={{
                      background: '#ffffff',
                      border: '1px solid #d1d5db',
                      color: '#0d0d0d',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '0.88rem',
                    }}
                  >
                    <option value="mixed">Mixed (MCQs & Short Answer)</option>
                    <option value="mcq">Multiple Choice Only</option>
                    <option value="short_answer">Short Conceptual Answer</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                    Difficulty
                  </label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as any)}
                    style={{
                      background: '#ffffff',
                      border: '1px solid #d1d5db',
                      color: '#0d0d0d',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '0.88rem',
                    }}
                  >
                    <option value="medium">Medium (Standard Exam)</option>
                    <option value="easy">Easy (Fundamentals)</option>
                    <option value="hard">Hard (Advanced / Competitive Level)</option>
                    <option value="mixed">Mixed (Graduated difficulty)</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Inline Error Message */}
          {formError && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: '#991b1b',
              fontSize: '0.85rem',
            }}>
              <span>{formError}</span>
              <button
                type="button"
                onClick={() => setFormError(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#991b1b',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                }}
              >
                ✕ Dismiss
              </button>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, borderTop: '1px solid #e5e7eb', paddingTop: 14 }}>
            <span style={{ fontSize: '0.82rem', color: '#6b7280' }}>
              Source context: {effectiveDocIds.length} document(s) active
            </span>
            <button
              onClick={handleRunTool}
              disabled={isLoading || effectiveDocIds.length === 0}
              className="btn btn-primary"
              style={{ padding: '9px 18px', borderRadius: '8px' }}
            >
              {isLoading ? 'Generating study material...' : 'Generate Study Material'}
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Prominent Loading Action Below Form */}
      {isLoading && (
        <div style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '16px',
          padding: '48px 24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: 16,
        }}>
          <div style={{
            width: 44,
            height: 44,
            border: '3px solid #e5e7eb',
            borderTop: '3px solid #0d0d0d',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0d0d0d', margin: '0 0 6px 0' }}>
              {activeTool === 'summarize' && (summaryTopic ? `Synthesizing Summary on "${summaryTopic}"...` : 'Synthesizing Comprehensive Document Summary...')}
              {activeTool === 'explain' && `Formulating In-Depth Explanation for "${concept}"...`}
              {activeTool === 'revision' && 'Compiling Exam Revision Notes, Formulas & Pitfalls...'}
              {activeTool === 'practice' && (practiceTopic ? `Generating Practice Questions for "${practiceTopic}"...` : 'Generating Practice Questions...')}
            </h3>
            <p style={{ fontSize: '0.88rem', color: '#6b7280', margin: 0, maxWidth: 540 }}>
              Retrieving grounded document evidence, structuring academic templates, and generating verified content...
            </p>
          </div>
        </div>
      )}

      {/* Generated Content Output */}
      {result && !isLoading && (
        <div style={{
          background: '#ffffff',
          border: '1px solid #e5e7eb',
          borderRadius: '16px',
          padding: '28px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, borderBottom: '1px solid #e5e7eb', paddingBottom: 14 }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0d0d0d', margin: 0 }}>
                {result.title}
              </h3>
              <span className="badge badge-verified" style={{ marginTop: 6 }}>
                Generated & Grounded in Document Chunks
              </span>
            </div>
            <button
              onClick={handleCopy}
              className="btn btn-secondary"
            >
              {copied ? <Check size={16} color="#059669" /> : <Copy size={16} />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
          </div>

          {(() => {
            let mcqs: McqItem[] = [];
            let remainingText = result.content || '';

            if (result.structured_content && Array.isArray(result.structured_content) && result.structured_content.length > 0 && result.structured_content[0]?.options) {
              mcqs = result.structured_content;
              const parsed = parseMcqsFromMarkdown(remainingText);
              remainingText = parsed.remainingText;
            } else if (activeTool === 'practice' || result.content_type === 'practice_questions') {
              const parsed = parseMcqsFromMarkdown(remainingText);
              if (parsed.mcqs.length > 0) {
                mcqs = parsed.mcqs;
                remainingText = parsed.remainingText;
              }
            }

            if (mcqs.length > 0) {
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <InteractiveMcqList questions={mcqs} title="Interactive Practice MCQs" />

                  {remainingText.trim() && (
                    <div style={{ marginTop: 14, paddingTop: 18, borderTop: '1px solid #e5e7eb' }}>
                      <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0d0d0d', marginBottom: 10 }}>
                        Additional Conceptual Questions
                      </div>
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {remainingText}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              );
            }

            return (
              <div className="markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.content}
                </ReactMarkdown>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};
