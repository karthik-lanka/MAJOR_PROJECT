import React, { useState } from 'react';
import { CheckCircle2, XCircle, RefreshCw, Award } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cleanMathText } from './ChatInterface';

export interface McqOption {
  id: string; // "A", "B", "C", "D"
  text: string;
}

export interface McqItem {
  id: string | number;
  question: string;
  options: McqOption[];
  correct_option: string;
  explanation?: string;
  difficulty?: string;
}

export function parseMcqsFromMarkdown(text: string): { mcqs: McqItem[]; remainingText: string } {
  if (!text) return { mcqs: [], remainingText: '' };

  const mcqs: McqItem[] = [];
  let workingText = text;

  // Regex to match MCQ questions formatted in markdown
  // Matches: Question header, question prompt, 4 options (A-D), correct option, and optional explanation
  const mcqRegex = /(?:###?\s*)?(?:Question\s*\d*[:.]?\s*(?:\(MCQ\)|Multiple Choice[^\n]*)?\n+)?([^\n]+(?:\n(?![•\-\*]?\s*[A-D][\)\.])[^\n]+)*)\n+[•\-\*]?\s*A[\)\.]\s*([^\n]+)\n+[•\-\*]?\s*B[\)\.]\s*([^\n]+)\n+[•\-\*]?\s*C[\)\.]\s*([^\n]+)\n+[•\-\*]?\s*D[\)\.]\s*([^\n]+)(?:\n+[•\-\*]?\s*(?:Correct\s*(?:Option|Answer)|Answer)[:\s]*([A-D])\b[^\n]*)?(?:\n+(?:Explanation|Reasoning)[:\s]*([^\n]+(?:\n(?!(?:Question|###|\d+\.))[^\n]+)*))?/gi;

  let match: RegExpExecArray | null;
  const matchesToRemove: string[] = [];

  while ((match = mcqRegex.exec(text)) !== null) {
    const rawQuestion = match[1]?.trim() || '';
    // Clean up "Question 1: " prefix if present in the prompt
    const cleanedQuestion = rawQuestion.replace(/^(?:Question\s*\d*[:.]?\s*(?:\(MCQ\)|Multiple Choice[^\n]*)?\s*)/i, '').trim();

    const optA = match[2]?.trim() || '';
    const optB = match[3]?.trim() || '';
    const optC = match[4]?.trim() || '';
    const optD = match[5]?.trim() || '';
    const correctOpt = (match[6]?.trim() || 'A').toUpperCase();
    const explanation = match[7]?.trim() || '';

    if (cleanedQuestion && optA && optB && optC && optD) {
      mcqs.push({
        id: `mcq_${mcqs.length + 1}`,
        question: cleanedQuestion,
        options: [
          { id: 'A', text: optA },
          { id: 'B', text: optB },
          { id: 'C', text: optC },
          { id: 'D', text: optD },
        ],
        correct_option: correctOpt,
        explanation: explanation || undefined,
      });
      matchesToRemove.push(match[0]);
    }
  }

  // Remove parsed MCQ blocks from working text so answers are not spoiled
  for (const block of matchesToRemove) {
    workingText = workingText.replace(block, '');
  }

  // Also remove generic headers like "Exam Questions and Solutions" or "Multiple Choice Questions:"
  workingText = workingText
    .replace(/#+\s*(?:Exam Questions and Solutions|Practice MCQs|Multiple Choice Questions)[^\n]*/gi, '')
    .trim();

  return { mcqs, remainingText: workingText };
}

interface InteractiveMcqListProps {
  questions: McqItem[];
  title?: string;
}

export const InteractiveMcqList: React.FC<InteractiveMcqListProps> = ({ questions, title }) => {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string | number, string>>({});

  if (!questions || questions.length === 0) return null;

  const handleSelect = (questionId: string | number, optionId: string) => {
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: optionId,
    }));
  };

  const handleReset = () => {
    setSelectedAnswers({});
  };

  const answeredCount = Object.keys(selectedAnswers).length;
  const correctCount = questions.filter(
    (q) => selectedAnswers[q.id] && selectedAnswers[q.id].toUpperCase() === q.correct_option?.toUpperCase()
  ).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, width: '100%' }}>
      {/* Quiz Progress & Score Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: '#f9fafb',
        border: '1px solid #e5e7eb',
        borderRadius: '12px',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Award size={18} color="#0d0d0d" />
          <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#0d0d0d' }}>
            {title || 'Interactive Practice MCQs'}
          </span>
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
            ({questions.length} questions)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {answeredCount > 0 && (
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0d0d0d' }}>
              Score: <span style={{ color: correctCount === answeredCount ? '#059669' : '#0d0d0d' }}>{correctCount}</span> / {answeredCount}
            </div>
          )}

          {answeredCount > 0 && (
            <button
              onClick={handleReset}
              className="btn btn-secondary"
              style={{ padding: '4px 10px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: 5 }}
            >
              <RefreshCw size={12} /> Reset
            </button>
          )}
        </div>
      </div>

      {/* Questions List */}
      {questions.map((q, idx) => {
        const questionKey = q.id ?? idx;
        const selectedOpt = selectedAnswers[questionKey];
        const isAnswered = !!selectedOpt;
        const normalizedCorrect = (q.correct_option || 'A').toUpperCase();

        return (
          <div
            key={questionKey}
            style={{
              background: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '14px',
              padding: '20px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            {/* Question Text */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 14 }}>
              <span style={{
                width: 26,
                height: 26,
                borderRadius: '50%',
                background: '#f3f4f6',
                color: '#111827',
                fontSize: '0.82rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                marginTop: 1,
              }}>
                {idx + 1}
              </span>
              <div style={{ fontSize: '0.94rem', fontWeight: 600, color: '#0d0d0d', lineHeight: 1.45, flex: 1 }}>
                {cleanMathText(q.question)}
              </div>
            </div>

            {/* Options Grid (Clickable) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 10 }}>
              {q.options.map((opt) => {
                const optId = opt.id.toUpperCase();
                const isSelected = selectedOpt?.toUpperCase() === optId;
                const isCorrect = optId === normalizedCorrect;

                let background = '#ffffff';
                let borderColor = '#e5e7eb';
                let textColor = '#111827';
                let icon = null;

                if (isAnswered) {
                  if (isCorrect) {
                    background = '#ecfdf5';
                    borderColor = '#10b981';
                    textColor = '#065f46';
                    icon = <CheckCircle2 size={16} color="#059669" style={{ flexShrink: 0 }} />;
                  } else if (isSelected) {
                    background = '#fef2f2';
                    borderColor = '#f87171';
                    textColor = '#991b1b';
                    icon = <XCircle size={16} color="#dc2626" style={{ flexShrink: 0 }} />;
                  }
                }

                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleSelect(questionKey, opt.id)}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '10px',
                      background,
                      border: `1px solid ${borderColor}`,
                      color: textColor,
                      textAlign: 'left',
                      fontSize: '0.86rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 8,
                      transition: 'all 0.15s ease',
                      boxShadow: isSelected ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
                    }}
                    onMouseEnter={(e) => {
                      if (!isAnswered) {
                        e.currentTarget.style.background = '#f9fafb';
                        e.currentTarget.style.borderColor = '#d1d5db';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isAnswered) {
                        e.currentTarget.style.background = '#ffffff';
                        e.currentTarget.style.borderColor = '#e5e7eb';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontWeight: 700,
                        color: isAnswered && isCorrect ? '#059669' : (isAnswered && isSelected ? '#dc2626' : '#6b7280'),
                        fontSize: '0.84rem',
                      }}>
                        {opt.id}.
                      </span>
                      <span>{cleanMathText(opt.text)}</span>
                    </div>
                    {icon}
                  </button>
                );
              })}
            </div>

            {/* Instant Answer Feedback & Explanation */}
            {isAnswered && (
              <div style={{
                marginTop: 14,
                padding: '12px 16px',
                borderRadius: '8px',
                background: selectedOpt.toUpperCase() === normalizedCorrect ? '#f0fdf4' : '#fffbeb',
                borderLeft: `4px solid ${selectedOpt.toUpperCase() === normalizedCorrect ? '#10b981' : '#f59e0b'}`,
                borderTop: '1px solid #e5e7eb',
                borderRight: '1px solid #e5e7eb',
                borderBottom: '1px solid #e5e7eb',
              }}>
                <div style={{
                  fontSize: '0.84rem',
                  fontWeight: 700,
                  color: selectedOpt.toUpperCase() === normalizedCorrect ? '#15803d' : '#b45309',
                  marginBottom: 4,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}>
                  {selectedOpt.toUpperCase() === normalizedCorrect ? (
                    <>Correct Answer!</>
                  ) : (
                    <>Incorrect (Correct: Option {normalizedCorrect})</>
                  )}
                </div>
                {q.explanation && (
                  <div style={{ fontSize: '0.83rem', color: '#374151', lineHeight: 1.5, marginTop: 4 }}>
                    <strong>Explanation: </strong>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {cleanMathText(q.explanation)}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
