import { useEffect, useRef } from 'react';
import { MessageCircle } from 'lucide-react';

interface ResponsePanelProps {
  responseText: string;
  isStreaming: boolean;
}

export function ResponsePanel({ responseText, isStreaming }: ResponsePanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [responseText]);

  return (
    <div className="flex-1 flex flex-col glass rounded-xl border border-white/10 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/5 text-xs text-[#94a3b8]">
        <MessageCircle size={14} />
        <span>AI Response</span>
        {isStreaming && (
          <span className="ml-auto text-[#7c3aed] animate-pulse">typing...</span>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3">
        {responseText ? (
          <div className="text-sm leading-relaxed text-[#f1f5f9]">
            {responseText}
            {isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-[#00e5ff] animate-pulse" />
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-12 h-12 rounded-full bg-[#1a2235] flex items-center justify-center mb-3">
              <MessageCircle size={20} className="text-[#64748b]" />
            </div>
            <p className="text-sm text-[#64748b] mb-1">Draw something and submit</p>
            <p className="text-xs text-[#64748b]/60">The AI will recognize your sketch</p>
          </div>
        )}
      </div>
    </div>
  );
}