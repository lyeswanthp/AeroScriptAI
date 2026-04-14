import type { Gesture } from '../types';
import { Hand, Pencil, Eraser, ThumbsUp } from 'lucide-react';

interface GestureIndicatorProps {
  currentGesture: Gesture;
}

const gestureConfig = [
  { gesture: 'idle' as Gesture, icon: Hand, color: '#64748b', label: 'Idle' },
  { gesture: 'draw' as Gesture, icon: Pencil, color: '#00e5ff', label: 'Draw' },
  { gesture: 'erase' as Gesture, icon: Eraser, color: '#f59e0b', label: 'Erase' },
  { gesture: 'submit' as Gesture, icon: ThumbsUp, color: '#10b981', label: 'Submit' },
];

export function GestureIndicator({ currentGesture }: GestureIndicatorProps) {
  return (
    <div className="h-10 flex items-center justify-center gap-2 px-4 glass border-t border-white/5">
      {gestureConfig.map(({ gesture, icon: Icon, color, label }) => {
        const isActive = currentGesture === gesture;
        return (
          <div
            key={gesture}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-all duration-150 ${
              isActive ? 'scale-105' : 'opacity-50'
            }`}
            style={{
              backgroundColor: isActive ? `${color}20` : 'transparent',
              border: `1px solid ${isActive ? color : 'transparent'}`,
            }}
          >
            <Icon
              size={16}
              style={{ color: isActive ? color : '#64748b' }}
              strokeWidth={isActive ? 2.5 : 1.5}
            />
            <span
              className="text-xs font-medium"
              style={{ color: isActive ? color : '#64748b' }}
            >
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}