import { useCallback, useRef, useState } from 'react';
import type { Stroke, Point } from '../types';

interface UseCanvasDrawingReturn {
  strokes: Stroke[];
  currentStroke: Stroke | null;
  isDrawing: boolean;
  startStroke: (point: Point, color: string, width: number) => void;
  addPoint: (point: Point) => void;
  endStroke: () => void;
  undo: () => void;
  clear: () => void;
  getStrokeCount: () => number;
}

const MAX_STROKES = 50;
const MIN_MOVEMENT_THRESHOLD = 5;

export function useCanvasDrawing(): UseCanvasDrawingReturn {
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [currentStroke, setCurrentStroke] = useState<Stroke | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const lastPointRef = useRef<Point | null>(null);
  const strokeBufferRef = useRef<Point[]>([]);

  const startStroke = useCallback((point: Point, color: string, width: number) => {
    lastPointRef.current = point;
    strokeBufferRef.current = [point];
    setCurrentStroke({ points: [point], color, width });
    setIsDrawing(true);
  }, []);

  const addPoint = useCallback((point: Point) => {
    if (!lastPointRef.current) return;

    const dx = point.x - lastPointRef.current.x;
    const dy = point.y - lastPointRef.current.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance >= MIN_MOVEMENT_THRESHOLD) {
      lastPointRef.current = point;
      strokeBufferRef.current.push(point);

      setCurrentStroke((prev) => {
        if (!prev) return null;
        return { ...prev, points: [...strokeBufferRef.current] };
      });
    }
  }, []);

  const endStroke = useCallback(() => {
    if (currentStroke && currentStroke.points.length > 1) {
      setStrokes((prev) => {
        const newStrokes = [...prev, currentStroke];
        if (newStrokes.length > MAX_STROKES) {
          return newStrokes.slice(-MAX_STROKES);
        }
        return newStrokes;
      });
    }
    setCurrentStroke(null);
    setIsDrawing(false);
    lastPointRef.current = null;
    strokeBufferRef.current = [];
  }, [currentStroke]);

  const undo = useCallback(() => {
    setStrokes((prev) => prev.slice(0, -1));
  }, []);

  const clear = useCallback(() => {
    setStrokes([]);
    setCurrentStroke(null);
    lastPointRef.current = null;
    strokeBufferRef.current = [];
  }, []);

  const getStrokeCount = useCallback(() => strokes.length, [strokes]);

  return {
    strokes,
    currentStroke,
    isDrawing,
    startStroke,
    addPoint,
    endStroke,
    undo,
    clear,
    getStrokeCount,
  };
}