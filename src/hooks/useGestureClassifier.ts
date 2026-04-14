import { useCallback, useRef, useState } from 'react';
import type { Gesture } from '../types';

interface UseGestureClassifierReturn {
  gesture: Gesture;
  thumbsUpStartRef: React.MutableRefObject<number | null>;
  classifyGesture: (landmarks: Array<{ x: number; y: number; z: number }>) => Gesture;
}

const LANDMARKS = {
  WRIST: 0,
  THUMB_TIP: 4,
  THUMB_IP: 3,
  INDEX_TIP: 8,
  INDEX_MCP: 5,
  MIDDLE_TIP: 12,
  MIDDLE_MCP: 9,
  RING_TIP: 16,
  RING_MCP: 13,
  PINKY_TIP: 20,
  PINKY_MCP: 17,
} as const;

const FINGER_EXTENDED_THRESHOLD = 0.06;
const THUMB_EXTENDED_THRESHOLD = 0.04;

export function useGestureClassifier(): UseGestureClassifierReturn {
  const [gesture, setGesture] = useState<Gesture>('idle');
  const thumbsUpStartRef = useRef<number | null>(null);
  const lastGestureRef = useRef<Gesture>('idle');

  const classifyGesture = useCallback((lm: Array<{ x: number; y: number; z: number }>): Gesture => {
    const wrist = lm[LANDMARKS.WRIST];
    const thumbTip = lm[LANDMARKS.THUMB_TIP];
    const thumbIP = lm[LANDMARKS.THUMB_IP];
    const indexTip = lm[LANDMARKS.INDEX_TIP];
    const indexMCP = lm[LANDMARKS.INDEX_MCP];
    const middleTip = lm[LANDMARKS.MIDDLE_TIP];
    const middleMCP = lm[LANDMARKS.MIDDLE_MCP];
    const ringTip = lm[LANDMARKS.RING_TIP];
    const ringMCP = lm[LANDMARKS.RING_MCP];
    const pinkyTip = lm[LANDMARKS.PINKY_TIP];
    const pinkyMCP = lm[LANDMARKS.PINKY_MCP];

    const indexExtended = indexTip.y < indexMCP.y - FINGER_EXTENDED_THRESHOLD;
    const middleExtended = middleTip.y < middleMCP.y - FINGER_EXTENDED_THRESHOLD;
    const ringExtended = ringTip.y < ringMCP.y - FINGER_EXTENDED_THRESHOLD;
    const pinkyExtended = pinkyTip.y < pinkyMCP.y - FINGER_EXTENDED_THRESHOLD;
    const thumbExtended = thumbTip.x < wrist.x - THUMB_EXTENDED_THRESHOLD && thumbTip.y < thumbIP.y;

    const extendedCount = [indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;

    // Thumbs up detection
    if (thumbExtended && !indexExtended && extendedCount === 0) {
      if (thumbsUpStartRef.current === null) {
        thumbsUpStartRef.current = Date.now();
      } else if (Date.now() - thumbsUpStartRef.current >= 2000) {
        lastGestureRef.current = 'submit';
        setGesture('submit');
        return 'submit';
      }
    } else {
      thumbsUpStartRef.current = null;
    }

    // Open palm
    if (indexExtended && middleExtended && ringExtended && pinkyExtended) {
      lastGestureRef.current = 'erase';
      setGesture('erase');
      return 'erase';
    }

    // Index pointing
    if (indexExtended && !middleExtended && !ringExtended && !pinkyExtended) {
      lastGestureRef.current = 'draw';
      setGesture('draw');
      return 'draw';
    }

    // Closed fist
    if (extendedCount === 0 && !thumbExtended) {
      lastGestureRef.current = 'idle';
      setGesture('idle');
      return 'idle';
    }

    setGesture(lastGestureRef.current);
    return lastGestureRef.current;
  }, []);

  return {
    gesture,
    thumbsUpStartRef,
    classifyGesture,
  };
}