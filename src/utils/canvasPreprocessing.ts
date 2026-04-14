import type { Stroke, Point } from '../types';

/**
 * Preprocess canvas strokes for VLM submission
 * Steps:
 * 1. Invert colors (black strokes on white)
 * 2. Crop to bounding box + 15% padding
 * 3. Resize to 512x512
 * 4. Thicken strokes to minimum 4px
 */
export function preprocessCanvas(
  strokes: Stroke[],
  sourceCanvas: HTMLCanvasElement
): { dataUrl: string; base64: string } {
  const tempCanvas = document.createElement('canvas');
  const ctx = tempCanvas.getContext('2d')!;

  const allPoints = strokes.flatMap((s) => s.points);
  if (allPoints.length === 0) {
    tempCanvas.width = 512;
    tempCanvas.height = 512;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 512, 512);
    const dataUrl = tempCanvas.toDataURL('image/png');
    return { dataUrl, base64: dataUrl.split(',')[1] || '' };
  }

  const minX = Math.min(...allPoints.map((p) => p.x));
  const maxX = Math.max(...allPoints.map((p) => p.x));
  const minY = Math.min(...allPoints.map((p) => p.y));
  const maxY = Math.max(...allPoints.map((p) => p.y));

  const padding = 0.15;
  const width = maxX - minX;
  const height = maxY - minY;
  const paddingX = width * padding;
  const paddingY = height * padding;

  const cropX = Math.max(0, minX - paddingX);
  const cropY = Math.max(0, minY - paddingY);
  const cropWidth = Math.min(sourceCanvas.width - cropX, width + paddingX * 2);
  const cropHeight = Math.min(sourceCanvas.height - cropY, height + paddingY * 2);

  const outputSize = 512;
  tempCanvas.width = outputSize;
  tempCanvas.height = outputSize;

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, outputSize, outputSize);

  ctx.fillStyle = '#000000';
  ctx.strokeStyle = '#000000';

  const scaleX = outputSize / cropWidth;
  const scaleY = outputSize / cropHeight;
  const scale = Math.min(scaleX, scaleY);

  strokes.forEach((stroke) => {
    if (stroke.points.length < 2) return;

    const minWidth = Math.max(4, stroke.width * scale);
    ctx.lineWidth = minWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    const firstPoint = stroke.points[0];
    ctx.moveTo((firstPoint.x - cropX) * scale, (firstPoint.y - cropY) * scale);

    for (let i = 1; i < stroke.points.length; i++) {
      const point = stroke.points[i];
      ctx.lineTo((point.x - cropX) * scale, (point.y - cropY) * scale);
    }
    ctx.stroke();
  });

  const dataUrl = tempCanvas.toDataURL('image/png');
  return { dataUrl, base64: dataUrl.split(',')[1] || '' };
}

/**
 * Apply stroke smoothing using Bezier curve fitting
 */
export function smoothPoints(points: Point[], tension = 0.5): Point[] {
  if (points.length < 3) return points;

  const smoothed: Point[] = [points[0]];

  for (let i = 1; i < points.length - 1; i++) {
    const p0 = points[i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];

    const smoothX = p1.x + tension * (p0.x - p2.x) * 0.25;
    const smoothY = p1.y + tension * (p0.y - p2.y) * 0.25;

    smoothed.push({ x: smoothX, y: smoothY });
  }

  smoothed.push(points[points.length - 1]);
  return smoothed;
}