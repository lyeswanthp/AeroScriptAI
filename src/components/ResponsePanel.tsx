import { useEffect, useRef, useState } from 'react';
import { MessageCircle, Send, Pencil } from 'lucide-react';
import type { ConversationMessage, ConfidenceLevel } from '../types';

interface ResponsePanelProps {
  messages: ConversationMessage[];
  isStreaming: boolean;
  isSubmitting: boolean;
  sessionId: string | null;
  confidence: ConfidenceLevel | null;
  onFollowUp: (text: string) => void;
}

const CONFIDENCE_COLORS: Record<ConfidenceLevel, string> = {
  high:    '#10b981',
  medium:  '#f59e0b',
  low:     '#ef4444',
  unknown: '#64748b',
};

const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  high:    'High',
  medium:  'Medium',
  low:     'Low',
  unknown: '?',
};

export function ResponsePanel({
  messages,
  isStreaming,
  isSubmitting,
  sessionId,
  confidence,
  onFollowUp,
}: ResponsePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState('');

  // Auto-scroll to bottom whenever messages or streaming content changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !sessionId || isStreaming || isSubmitting) return;
    setInput('');
    onFollowUp(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;
  const canSendFollowUp = !!sessionId && !isStreaming && !isSubmitting;

  return (
    <div className="flex-1 flex flex-col glass rounded-xl border border-white/10 overflow-hidden min-h-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/5 text-xs text-[#94a3b8] shrink-0">
        <MessageCircle size={14} />
        <span>AI Response</span>

        {/* Confidence badge */}
        {confidence && (
          <span
            className="ml-auto px-2 py-0.5 rounded-full text-[10px] font-bold uppercase"
            style={{
              backgroundColor: `${CONFIDENCE_COLORS[confidence]}20`,
              color: CONFIDENCE_COLORS[confidence],
            }}
          >
            {CONFIDENCE_LABELS[confidence]}
          </span>
        )}

        {/* Streaming indicator */}
        {isStreaming && !confidence && (
          <span className="ml-auto text-[#7c3aed] animate-pulse text-[10px]">typing…</span>
        )}
        {isStreaming && confidence && (
          <span className="text-[#7c3aed] animate-pulse text-[10px]">typing…</span>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-12 h-12 rounded-full bg-[#1a2235] flex items-center justify-center mb-3">
              <MessageCircle size={20} className="text-[#64748b]" />
            </div>
            <p className="text-sm text-[#64748b] mb-1">Draw something and submit</p>
            <p className="text-xs text-[#64748b]/60">Hold thumbs up for 2 s to send</p>
          </div>
        ) : (
          messages.map((msg, i) => {
            const isLastAssistant =
              msg.role === 'assistant' && i === messages.length - 1;
            const showCursor = isLastAssistant && isStreaming;

            if (msg.role === 'user') {
              return (
                <div key={i} className="flex items-start gap-2 justify-end">
                  <div
                    className="max-w-[90%] px-2.5 py-1.5 rounded-xl text-xs text-[#0a0e17] font-medium"
                    style={{ backgroundColor: '#00e5ff' }}
                  >
                    {msg.isDrawing ? (
                      <span className="flex items-center gap-1">
                        <Pencil size={10} />
                        Sketch submitted
                      </span>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              );
            }

            return (
              <div key={i} className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-[#1a2235] flex items-center justify-center shrink-0 mt-0.5">
                  <MessageCircle size={10} className="text-[#7c3aed]" />
                </div>
                <div className="text-xs leading-relaxed text-[#f1f5f9] flex-1">
                  {msg.content || (showCursor ? '' : <span className="text-[#64748b] italic">…</span>)}
                  {showCursor && (
                    <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-[#00e5ff] animate-pulse align-middle" />
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Follow-up input — only shown after first recognition */}
      {sessionId && (
        <div className="shrink-0 px-2 pb-2 pt-1 border-t border-white/5">
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!canSendFollowUp}
              placeholder={canSendFollowUp ? 'Ask a follow-up…' : 'Waiting…'}
              className="flex-1 min-w-0 bg-[#1a2235] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00e5ff]/50 disabled:opacity-40 disabled:cursor-not-allowed"
            />
            <button
              onClick={handleSend}
              disabled={!canSendFollowUp || !input.trim()}
              className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ backgroundColor: canSendFollowUp && input.trim() ? '#00e5ff' : '#1a2235' }}
            >
              <Send
                size={12}
                className={canSendFollowUp && input.trim() ? 'text-[#0a0e17]' : 'text-[#64748b]'}
              />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
