import { useEffect, useState } from 'react';
import type { CNNPrediction } from '../types';
import { Brain, Loader2 } from 'lucide-react';

interface PredictionPanelProps {
  predictions: CNNPrediction[];
  isLoading: boolean;
  hasEnoughStrokes: boolean;
}

export function PredictionPanel({ predictions, isLoading, hasEnoughStrokes }: PredictionPanelProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (!hasEnoughStrokes && predictions.length === 0) {
      const timer = setTimeout(() => setVisible(false), 2000);
      return () => clearTimeout(timer);
    }
    setVisible(true);
  }, [hasEnoughStrokes, predictions.length]);

  if (!visible) return null;

  return (
    <div className="w-64 p-3 glass rounded-xl border border-white/10 flex flex-col gap-3">
      <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
        <Brain size={14} />
        <span>Real-time CNN</span>
      </div>

      <div className="flex flex-col gap-2">
        {isLoading ? (
          <div className="flex items-center gap-2 text-[#64748b]">
            <Loader2 size={14} className="animate-spin" />
            <span className="text-xs">Analyzing...</span>
          </div>
        ) : predictions.length > 0 ? (
          predictions.slice(0, 3).map((pred, index) => (
            <div
              key={pred.category}
              className="animate-fade-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium capitalize">{pred.category}</span>
                <span className="text-xs text-[#94a3b8] font-mono">
                  {(pred.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 bg-[#1a2235] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#00e5ff] to-[#7c3aed] rounded-full transition-all duration-300"
                  style={{ width: `${pred.confidence * 100}%` }}
                />
              </div>
            </div>
          ))
        ) : (
          <div className="text-xs text-[#64748b] text-center py-4">
            {hasEnoughStrokes ? 'Keep drawing...' : 'Draw more to see predictions'}
          </div>
        )}
      </div>

      <div className="text-[10px] text-[#64748b]/60 text-center">
        DoodleNet • 345 categories
      </div>
    </div>
  );
}