import { Undo2, Trash2, Send, ChevronLeft, ChevronRight } from 'lucide-react';
import { COLORS } from '../types';

interface ToolbarProps {
  strokeColor: string;
  strokeWidth: number;
  canUndo: boolean;
  canClear: boolean;
  isSubmitting: boolean;
  onColorChange: (color: string) => void;
  onWidthChange: (width: number) => void;
  onUndo: () => void;
  onClear: () => void;
  onSubmit: () => void;
}

export function Toolbar({
  strokeColor,
  strokeWidth,
  canUndo,
  canClear,
  isSubmitting,
  onColorChange,
  onWidthChange,
  onUndo,
  onClear,
  onSubmit,
}: ToolbarProps) {
  return (
    <div className="h-14 flex items-center justify-between px-4 glass border-t border-white/5">
      {/* Color Picker */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 p-1 bg-[#0a0e17] rounded-lg">
          {COLORS.map((color) => (
            <button
              key={color}
              onClick={() => onColorChange(color)}
              className={`w-6 h-6 rounded-full transition-all duration-150 ${
                strokeColor === color ? 'ring-2 ring-offset-2 ring-offset-[#0a0e17] scale-110' : 'hover:scale-110'
              }`}
              style={{
                backgroundColor: color,
                outline: color === '#000000' ? '1px solid #ffffff40' : 'none',
              }}
              title={color}
            />
          ))}
        </div>

        <div className="ml-2 flex items-center gap-2">
          <div
            className="w-4 h-4 rounded border border-white/20"
            style={{ backgroundColor: strokeColor }}
          />
        </div>
      </div>

      {/* Stroke Width */}
      <div className="flex items-center gap-3">
        <ChevronLeft size={16} className="text-[#64748b]" />
        <div className="flex items-center gap-2">
          <input
            type="range"
            min="1"
            max="20"
            value={strokeWidth}
            onChange={(e) => onWidthChange(Number(e.target.value))}
            className="w-32 h-2 appearance-none bg-[#1a2235] rounded-full cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-4
              [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:bg-[#00e5ff]
              [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(0,229,255,0.5)]
              [&::-webkit-slider-thumb]:cursor-pointer
              [&::-webkit-slider-thumb]:transition-transform
              [&::-webkit-slider-thumb]:hover:scale-110"
          />
          <span className="text-xs text-[#94a3b8] w-6 text-right font-mono">
            {strokeWidth}
          </span>
        </div>
        <ChevronRight size={16} className="text-[#64748b]" />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className={`p-2 rounded-lg transition-all duration-150 ${
            canUndo
              ? 'bg-[#1a2235] hover:bg-[#1a2235]/80 text-[#94a3b8] hover:text-white'
              : 'bg-[#0a0e17] text-[#64748b]/40 cursor-not-allowed'
          }`}
          title="Undo (Ctrl+Z)"
        >
          <Undo2 size={18} />
        </button>

        <button
          onClick={onClear}
          disabled={!canClear}
          className={`p-2 rounded-lg transition-all duration-150 ${
            canClear
              ? 'bg-[#1a2235] hover:bg-red-500/20 text-[#94a3b8] hover:text-red-400'
              : 'bg-[#0a0e17] text-[#64748b]/40 cursor-not-allowed'
          }`}
          title="Clear Canvas"
        >
          <Trash2 size={18} />
        </button>

        <button
          onClick={onSubmit}
          disabled={isSubmitting}
          className={`ml-2 px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition-all duration-150 ${
            isSubmitting
              ? 'bg-[#10b981]/50 text-white/50 cursor-wait'
              : 'bg-[#10b981] hover:bg-[#10b981]/90 text-white glow-emerald hover:scale-105'
          }`}
        >
          <Send size={16} />
          {isSubmitting ? 'Sending...' : 'Submit'}
        </button>
      </div>
    </div>
  );
}