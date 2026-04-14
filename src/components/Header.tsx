import type { Mode } from '../types';

interface HeaderProps {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  isConnected: boolean;
}

export function Header({ mode, onModeChange, isConnected }: HeaderProps) {
  return (
    <header className="h-12 flex items-center justify-between px-4 glass border-b border-white/5">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className="text-[#00e5ff]">
          <path
            d="M14 2L26 8v12l-12 6L2 20V8l12-6z"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
          />
          <path
            d="M14 8l6 3v6l-6 3-6-3V11l6-3z"
            fill="currentColor"
            opacity="0.3"
          />
          <circle cx="14" cy="14" r="3" fill="currentColor" />
        </svg>
        <span className="font-bold text-lg tracking-tight">AeroScript AI</span>
      </div>

      {/* Mode Selector */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <select
            value={mode}
            onChange={(e) => onModeChange(e.target.value as Mode)}
            className="appearance-none bg-[#1a2235] border border-white/10 rounded-lg px-3 py-1.5 pr-8 text-sm cursor-pointer hover:border-white/20 transition-colors focus:outline-none focus:border-[#00e5ff]/50"
          >
            <option value="free">Free</option>
            <option value="object">Object</option>
            <option value="geography">Geography</option>
            <option value="math">Math</option>
          </select>
          <svg
            className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8] pointer-events-none"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        {/* Connection Status */}
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-[#10b981] animate-pulse-glow' : 'bg-[#64748b]'
            }`}
          />
          <span className="text-xs text-[#94a3b8]">
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  );
}