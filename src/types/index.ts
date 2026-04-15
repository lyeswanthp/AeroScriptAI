export type Gesture = 'idle' | 'draw' | 'erase' | 'submit';

export type Mode = 'free' | 'object' | 'geography' | 'math';

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'unknown';

export interface Point {
  x: number;
  y: number;
}

export interface Stroke {
  points: Point[];
  color: string;
  width: number;
}

export interface HandLandmarks {
  landmarks: Array<{ x: number; y: number; z: number }>;
  worldLandmarks: Array<{ x: number; y: number; z: number }>;
  handedness: 'Left' | 'Right';
  score: number;
}

export interface CNNPrediction {
  category: string;
  confidence: number;
}

export interface ProcessedImage {
  dataUrl: string;
  base64: string;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  /** True when the user message represents a drawing submission, not typed text. */
  isDrawing?: boolean;
  timestamp: number;
}

export interface AppState {
  gesture: Gesture;
  mode: Mode;
  strokeColor: string;
  strokeWidth: number;
  strokes: Stroke[];
  isConnected: boolean;
  isSubmitting: boolean;
  predictions: CNNPrediction[];
  responseText: string;
  conversationHistory: ConversationMessage[];
}

export const COLORS = [
  '#00e5ff', // cyan (default)
  '#d946ef', // magenta
  '#facc15', // yellow
  '#22c55e', // green
  '#fb923c', // orange
  '#f472b6', // pink
  '#ffffff', // white
  '#000000', // black
] as const;

export const GESTURE_LABELS: Record<Gesture, string> = {
  idle: 'Idle',
  draw: 'Draw',
  erase: 'Erase',
  submit: 'Submit',
};

export const MODE_LABELS: Record<Mode, string> = {
  free: 'Free',
  object: 'Object',
  geography: 'Geography',
  math: 'Math',
};