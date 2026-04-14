import { useState, useRef, useCallback, useEffect } from 'react';
import { Header } from './components/Header';
import { Toolbar } from './components/Toolbar';
import { GestureIndicator } from './components/GestureIndicator';
import { PredictionPanel } from './components/PredictionPanel';
import { ResponsePanel } from './components/ResponsePanel';
import type { Gesture, Mode, CNNPrediction, Point, Stroke } from './types';

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

const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17],
];

function App() {
  const [mode, setMode] = useState<Mode>('free');
  const [gesture, setGesture] = useState<Gesture>('idle');
  const [strokeColor, setStrokeColor] = useState('#00e5ff');
  const [strokeWidth, setStrokeWidth] = useState(3);
  const [isConnected] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [predictions] = useState<CNNPrediction[]>([]);
  const [responseText, setResponseText] = useState('');
  const [isStreaming] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [handsReady, setHandsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Drawing state
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [currentStroke, setCurrentStroke] = useState<Stroke | null>(null);

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mainCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const thumbsUpStartRef = useRef<number | null>(null);
  const lastGestureRef = useRef<Gesture>('idle');
  const lastIndexTipRef = useRef<Point | null>(null);
  const canvasSizeRef = useRef({ width: 0, height: 0 });
  const handsInstanceRef = useRef<any>(null);
  const isDrawingRef = useRef(false);

  // Draw hand skeleton
  const drawHandSkeleton = useCallback((
    ctx: CanvasRenderingContext2D,
    lm: Array<{ x: number; y: number; z?: number }>
  ) => {
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 1.5;
    ctx.fillStyle = '#00e5ff';

    HAND_CONNECTIONS.forEach(([start, end]) => {
      const p1 = lm[start];
      const p2 = lm[end];
      if (p1 && p2) {
        ctx.beginPath();
        ctx.moveTo((1 - p1.x) * ctx.canvas.width, p1.y * ctx.canvas.height);
        ctx.lineTo((1 - p2.x) * ctx.canvas.width, p2.y * ctx.canvas.height);
        ctx.stroke();
      }
    });

    lm.forEach((l) => {
      ctx.beginPath();
      ctx.arc((1 - l.x) * ctx.canvas.width, l.y * ctx.canvas.height, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  }, []);

  // Render all strokes to canvas
  const renderStrokes = useCallback(() => {
    const canvas = mainCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Render completed strokes
    strokes.forEach(stroke => {
      if (stroke.points.length < 2) return;
      ctx.beginPath();
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      for (let i = 1; i < stroke.points.length - 1; i++) {
        const xc = (stroke.points[i].x + stroke.points[i + 1].x) / 2;
        const yc = (stroke.points[i].y + stroke.points[i + 1].y) / 2;
        ctx.quadraticCurveTo(stroke.points[i].x, stroke.points[i].y, xc, yc);
      }
      ctx.lineTo(stroke.points[stroke.points.length - 1].x, stroke.points[stroke.points.length - 1].y);
      ctx.stroke();
    });

    // Render current stroke
    if (currentStroke && currentStroke.points.length >= 2) {
      ctx.beginPath();
      ctx.strokeStyle = currentStroke.color;
      ctx.lineWidth = currentStroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.moveTo(currentStroke.points[0].x, currentStroke.points[0].y);
      for (let i = 1; i < currentStroke.points.length - 1; i++) {
        const xc = (currentStroke.points[i].x + currentStroke.points[i + 1].x) / 2;
        const yc = (currentStroke.points[i].y + currentStroke.points[i + 1].y) / 2;
        ctx.quadraticCurveTo(currentStroke.points[i].x, currentStroke.points[i].y, xc, yc);
      }
      ctx.lineTo(currentStroke.points[currentStroke.points.length - 1].x, currentStroke.points[currentStroke.points.length - 1].y);
      ctx.stroke();
    }
  }, [strokes, currentStroke]);

  // Drawing functions
  const startStroke = useCallback((point: Point, color: string, width: number) => {
    setCurrentStroke({ points: [point], color, width });
    isDrawingRef.current = true;
  }, []);

  const addPoint = useCallback((point: Point) => {
    setCurrentStroke(prev => {
      if (!prev) return null;
      const dx = point.x - prev.points[prev.points.length - 1].x;
      const dy = point.y - prev.points[prev.points.length - 1].y;
      if (Math.sqrt(dx * dx + dy * dy) < 8) return prev;
      return { ...prev, points: [...prev.points, point] };
    });
  }, []);

  const endStroke = useCallback(() => {
    if (currentStroke && currentStroke.points.length > 1) {
      setStrokes(prev => [...prev.slice(-49), currentStroke]);
    }
    setCurrentStroke(null);
    isDrawingRef.current = false;
  }, [currentStroke]);

  const undo = useCallback(() => {
    setStrokes(prev => prev.slice(0, -1));
  }, []);

  const clear = useCallback(() => {
    setStrokes([]);
    setCurrentStroke(null);
    isDrawingRef.current = false;
  }, []);

  // Gesture classification
  const classifyGesture = useCallback((lm: Array<{ x: number; y: number; z?: number }>) => {
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

    if (!wrist || !thumbTip || !indexTip || !indexMCP) return lastGestureRef.current;

    const indexExtended = indexTip.y < indexMCP.y - FINGER_EXTENDED_THRESHOLD;
    const middleExtended = middleTip && middleMCP ? middleTip.y < middleMCP.y - FINGER_EXTENDED_THRESHOLD : false;
    const ringExtended = ringTip && ringMCP ? ringTip.y < ringMCP.y - FINGER_EXTENDED_THRESHOLD : false;
    const pinkyExtended = pinkyTip && pinkyMCP ? pinkyTip.y < pinkyMCP.y - FINGER_EXTENDED_THRESHOLD : false;
    const thumbExtended = thumbIP ? (thumbTip.x < wrist.x - THUMB_EXTENDED_THRESHOLD && thumbTip.y < thumbIP.y) : (thumbTip.x < wrist.x - THUMB_EXTENDED_THRESHOLD);

    const extendedCount = [indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;

    if (thumbExtended && !indexExtended && extendedCount === 0) {
      if (thumbsUpStartRef.current === null) {
        thumbsUpStartRef.current = Date.now();
      } else if (Date.now() - thumbsUpStartRef.current >= 2000) {
        return 'submit';
      }
    } else {
      thumbsUpStartRef.current = null;
    }

    if (indexExtended && middleExtended && ringExtended && pinkyExtended) return 'erase';
    if (indexExtended && !middleExtended && !ringExtended && !pinkyExtended) return 'draw';
    if (extendedCount === 0 && !thumbExtended) return 'idle';

    return lastGestureRef.current;
  }, []);

  const handleSubmit = useCallback(async () => {
    if (strokes.length === 0 || isSubmitting) return;
    setIsSubmitting(true);

    const { preprocessCanvas } = await import('./utils/canvasPreprocessing');
    preprocessCanvas(strokes, mainCanvasRef.current!);

    setTimeout(() => {
      setResponseText('Demo mode: Canvas exported. Connect backend for AI recognition.');
      setIsSubmitting(false);
    }, 1000);
  }, [strokes, isSubmitting]);

  // Process hand landmarks
  const processHands = useCallback((lm: Array<{ x: number; y: number; z?: number }>, gesture: Gesture) => {
    const { width, height } = canvasSizeRef.current;
    const indexTip = lm[LANDMARKS.INDEX_TIP];
    if (indexTip && width > 0 && height > 0) {
      // Since video is mirrored, hand on left of video = user's right side
      lastIndexTipRef.current = { x: (1 - indexTip.x) * width, y: indexTip.y * height };
    }

    const prevGesture = lastGestureRef.current;
    lastGestureRef.current = gesture;
    setGesture(gesture);

    // Handle gesture changes
    if (gesture === 'draw' && prevGesture !== 'draw') {
      if (lastIndexTipRef.current) {
        startStroke(lastIndexTipRef.current, strokeColor, strokeWidth);
      }
    } else if (gesture === 'draw' && lastIndexTipRef.current && isDrawingRef.current) {
      addPoint(lastIndexTipRef.current);
    } else if (gesture === 'idle' && isDrawingRef.current) {
      endStroke();
    } else if (gesture === 'erase' && strokes.length > 0) {
      clear();
    } else if (gesture === 'submit' && prevGesture !== 'submit') {
      handleSubmit();
    }
  }, [strokeColor, strokeWidth, startStroke, addPoint, endStroke, clear, handleSubmit, strokes.length]);

  // Initialize MediaPipe Hands
  useEffect(() => {
    const initHands = async () => {
      try {
        const loadScript = (src: string): Promise<void> => {
          return new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing) { resolve(); return; }
            const script = document.createElement('script');
            script.src = src;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`Failed to load ${src}`));
            document.head.appendChild(script);
          });
        };

        await loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.min.js');

        let attempts = 0;
        while (!(window as any).Hands && attempts < 50) {
          await new Promise(r => setTimeout(r, 100));
          attempts++;
        }

        if (!(window as any).Hands) {
          throw new Error('Failed to load MediaPipe Hands');
        }

        const Hands = (window as any).Hands;
        handsInstanceRef.current = new Hands({
          locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/${file}`,
        });

        handsInstanceRef.current.setOptions({
          maxNumHands: 1,
          modelComplexity: 1,
          minDetectionConfidence: 0.7,
          minTrackingConfidence: 0.5,
        });

        handsInstanceRef.current.onResults((results: any) => {
          const overlayCanvas = overlayCanvasRef.current;
          if (!overlayCanvas) return;

          const ctx = overlayCanvas.getContext('2d');
          if (!ctx) return;

          // Update canvas size
          const rect = overlayCanvas.getBoundingClientRect();
          if (overlayCanvas.width !== rect.width || overlayCanvas.height !== rect.height) {
            overlayCanvas.width = rect.width;
            overlayCanvas.height = rect.height;
          }
          canvasSizeRef.current = { width: rect.width, height: rect.height };

          ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

          if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            const lm = results.multiHandLandmarks[0];
            drawHandSkeleton(ctx, lm);
            const gesture = classifyGesture(lm);
            processHands(lm, gesture);
          } else {
            if (lastGestureRef.current !== 'idle') {
              lastGestureRef.current = 'idle';
              setGesture('idle');
              thumbsUpStartRef.current = null;
              if (isDrawingRef.current) {
                endStroke();
              }
            }
          }
        });

        setHandsReady(true);
        console.log('MediaPipe Hands ready');
      } catch (err) {
        console.error('Failed to initialize:', err);
        setError('Failed to load hand tracking');
      }
    };

    initHands();

    return () => {
      if (handsInstanceRef.current) {
        handsInstanceRef.current.close();
      }
    };
  }, [drawHandSkeleton, classifyGesture, processHands, endStroke]);

  // Start camera
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: 'user' },
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = async () => {
            await videoRef.current!.play();
            setCameraReady(true);
          };
        }
      } catch (err) {
        console.error('Camera error:', err);
        setError('Camera access denied');
      }
    };

    startCamera();

    return () => {
      if (videoRef.current?.srcObject) {
        (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  // Process video frames (throttled to ~30fps for smoother drawing)
  useEffect(() => {
    if (!cameraReady || !handsReady) return;

    let animFrame: number;
    let lastTime = 0;
    const targetFPS = 30;
    const interval = 1000 / targetFPS;

    const processFrame = async (timestamp: number) => {
      if (timestamp - lastTime >= interval) {
        lastTime = timestamp;
        if (videoRef.current && handsInstanceRef.current && videoRef.current.readyState >= 2) {
          try {
            await handsInstanceRef.current.send({ image: videoRef.current });
          } catch (e) {
            // Ignore errors
          }
        }
      }
      animFrame = requestAnimationFrame(processFrame);
    };

    processFrame(0);

    return () => {
      if (animFrame) cancelAnimationFrame(animFrame);
    };
  }, [cameraReady, handsReady]);

  // Render strokes when they change
  useEffect(() => {
    renderStrokes();
  }, [renderStrokes]);

  // Handle resize
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        canvasSizeRef.current = { width: rect.width, height: rect.height };
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        undo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo]);

  const getGestureColor = () => {
    switch (gesture) {
      case 'draw': return '#00e5ff';
      case 'erase': return '#f59e0b';
      case 'submit': return '#10b981';
      default: return '#64748b';
    }
  };

  const isLoading = !cameraReady || !handsReady;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0a0e17]">
      <Header mode={mode} onModeChange={setMode} isConnected={isConnected} />

      <div className="flex flex-1 overflow-hidden">
        <div
          ref={containerRef}
          className="relative flex-1 overflow-hidden"
          style={{
            borderColor: getGestureColor(),
            borderWidth: '2px',
            borderStyle: 'solid',
            transition: 'border-color 150ms ease-out',
          }}
        >
          <div className="absolute inset-0 bg-grid opacity-30" />

          {isLoading && !error && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e17]/90 z-20">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-[#00e5ff] border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-[#94a3b8]">
                  {!handsReady ? 'Loading hand tracking...' : 'Starting camera...'}
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e17]/90 z-20">
              <div className="text-center">
                <p className="text-red-400 mb-2">{error}</p>
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-[#00e5ff] text-[#0a0e17] rounded-lg"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          <video
            ref={videoRef}
            className="absolute inset-0 w-full h-full object-cover"
            style={{ opacity: 0.35, transform: 'scaleX(-1)' }}
            playsInline
            muted
          />

          <canvas
            ref={mainCanvasRef}
            className="absolute inset-0 w-full h-full"
            style={{ background: 'transparent' }}
          />

          <canvas
            ref={overlayCanvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
          />

          <div className="absolute top-3 right-3 px-3 py-1.5 rounded-full glass text-xs font-medium z-10">
            <span style={{ color: getGestureColor() }}>{gesture.toUpperCase()}</span>
          </div>

          <div className="absolute bottom-4 left-4 w-48 h-36 rounded-xl overflow-hidden glass border border-white/10 z-10">
            <video ref={videoRef} className="w-full h-full object-cover" style={{ transform: 'scaleX(-1)' }} playsInline muted />
            <div
              className="absolute bottom-2 right-2 px-2 py-1 rounded-full text-[10px] font-bold uppercase"
              style={{ backgroundColor: `${getGestureColor()}30`, color: getGestureColor() }}
            >
              {gesture}
            </div>
            <div className="absolute top-2 left-2 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-[10px] text-white/60 font-medium">LIVE</span>
            </div>
          </div>
        </div>

        <div className="w-64 flex flex-col gap-3 p-3 border-l border-white/5">
          <PredictionPanel
            predictions={predictions}
            isLoading={false}
            hasEnoughStrokes={strokes.length >= 10}
          />
          <ResponsePanel responseText={responseText} isStreaming={isStreaming} />
        </div>
      </div>

      <GestureIndicator currentGesture={gesture} />

      <Toolbar
        strokeColor={strokeColor}
        strokeWidth={strokeWidth}
        canUndo={strokes.length > 0}
        canClear={strokes.length > 0}
        isSubmitting={isSubmitting}
        onColorChange={setStrokeColor}
        onWidthChange={setStrokeWidth}
        onUndo={undo}
        onClear={clear}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

export default App;