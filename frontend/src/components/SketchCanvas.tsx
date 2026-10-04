import React, { useRef, useState, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';

export interface SketchCanvasHandle {
  getBlob: () => Promise<Blob | null>;
  isEmpty: () => boolean;
  clear: () => void;
  loadPreset: (type: 'chair' | 'table' | 'lamp' | 'mug') => void;
}

interface Point {
  x: number;
  y: number;
}

interface Stroke {
  points: Point[];
  size: number;
  isEraser: boolean;
}

export const SketchCanvas = forwardRef<SketchCanvasHandle, { onStrokeChange?: (hasStrokes: boolean) => void }>(
  ({ onStrokeChange }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [brushSize, setBrushSize] = useState<number>(4);
    const [isEraser, setIsEraser] = useState<boolean>(false);
    const [strokes, setStrokes] = useState<Stroke[]>([]);
    const [redoStack, setRedoStack] = useState<Stroke[]>([]);
    const currentStroke = useRef<Stroke | null>(null);

    // Re-render canvas from strokes
    const redrawCanvas = useCallback(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const rect = canvas.getBoundingClientRect();

      // Fill light background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, rect.width, rect.height);

      // Draw subtle grid guides for industrial sketching
      ctx.strokeStyle = '#f1f5f9';
      ctx.lineWidth = 1;
      const gridSize = 32;
      for (let x = gridSize; x < rect.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, rect.height);
        ctx.stroke();
      }
      for (let y = gridSize; y < rect.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(rect.width, y);
        ctx.stroke();
      }

      // Draw all committed strokes
      const allStrokes = currentStroke.current ? [...strokes, currentStroke.current] : strokes;
      for (const stroke of allStrokes) {
        if (stroke.points.length < 1) continue;
        ctx.beginPath();
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.lineWidth = stroke.size;
        ctx.strokeStyle = stroke.isEraser ? '#ffffff' : '#111827';

        const p0 = stroke.points[0];
        ctx.moveTo(p0.x, p0.y);
        for (let i = 1; i < stroke.points.length; i++) {
          const pt = stroke.points[i];
          ctx.lineTo(pt.x, pt.y);
        }
        ctx.stroke();
      }
    }, [strokes]);

    // Handle high-DPI resize
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const resize = () => {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.scale(dpr, dpr);
        }
        redrawCanvas();
      };

      resize();
      window.addEventListener('resize', resize);
      return () => window.removeEventListener('resize', resize);
    }, [redrawCanvas]);

    useEffect(() => {
      redrawCanvas();
      onStrokeChange?.(strokes.length > 0);
    }, [strokes, redrawCanvas, onStrokeChange]);

    const getCanvasPoint = (e: React.MouseEvent | React.TouchEvent): Point | null => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();

      let clientX = 0;
      let clientY = 0;

      if ('touches' in e) {
        if (e.touches.length === 0) return null;
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
      } else {
        clientX = e.clientX;
        clientY = e.clientY;
      }

      return {
        x: clientX - rect.left,
        y: clientY - rect.top,
      };
    };

    const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
      if ('touches' in e) {
        // Prevent touch scroll
        e.preventDefault();
      }
      const pt = getCanvasPoint(e);
      if (!pt) return;

      setIsDrawing(true);
      currentStroke.current = {
        points: [pt],
        size: brushSize,
        isEraser: isEraser,
      };
      redrawCanvas();
    };

    const draw = (e: React.MouseEvent | React.TouchEvent) => {
      if (!isDrawing || !currentStroke.current) return;
      if ('touches' in e) {
        e.preventDefault();
      }
      const pt = getCanvasPoint(e);
      if (!pt) return;

      currentStroke.current.points.push(pt);
      redrawCanvas();
    };

    const stopDrawing = () => {
      if (!isDrawing) return;
      setIsDrawing(false);
      if (currentStroke.current && currentStroke.current.points.length > 0) {
        setStrokes((prev) => [...prev, currentStroke.current!]);
        setRedoStack([]); // clear redo on new action
      }
      currentStroke.current = null;
    };

    const handleUndo = () => {
      if (strokes.length === 0) return;
      const last = strokes[strokes.length - 1];
      setStrokes((prev) => prev.slice(0, prev.length - 1));
      setRedoStack((prev) => [...prev, last]);
    };

    const handleRedo = () => {
      if (redoStack.length === 0) return;
      const last = redoStack[redoStack.length - 1];
      setRedoStack((prev) => prev.slice(0, prev.length - 1));
      setStrokes((prev) => [...prev, last]);
    };

    const handleClear = () => {
      if (strokes.length === 0) return;
      setStrokes([]);
      setRedoStack([]);
    };

    const loadPreset = (type: 'chair' | 'table' | 'lamp' | 'mug') => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const cx = w / 2;
      const cy = h / 2;

      let presetStrokes: Stroke[] = [];

      if (type === 'chair') {
        presetStrokes = [
          // Backrest vertical posts
          { points: [{ x: cx - 50, y: cy - 90 }, { x: cx - 50, y: cy + 10 }], size: 5, isEraser: false },
          { points: [{ x: cx + 50, y: cy - 90 }, { x: cx + 50, y: cy + 10 }], size: 5, isEraser: false },
          // Backrest top rail & splats
          { points: [{ x: cx - 52, y: cy - 85 }, { x: cx + 52, y: cy - 85 }], size: 6, isEraser: false },
          { points: [{ x: cx - 25, y: cy - 85 }, { x: cx - 25, y: cy + 10 }], size: 3, isEraser: false },
          { points: [{ x: cx + 25, y: cy - 85 }, { x: cx + 25, y: cy + 10 }], size: 3, isEraser: false },
          // Seat cushion / plane
          { points: [{ x: cx - 60, y: cy + 10 }, { x: cx + 60, y: cy + 10 }, { x: cx + 50, y: cy + 25 }, { x: cx - 50, y: cy + 25 }, { x: cx - 60, y: cy + 10 }], size: 5, isEraser: false },
          // Four legs
          { points: [{ x: cx - 55, y: cy + 25 }, { x: cx - 55, y: cy + 100 }], size: 5, isEraser: false },
          { points: [{ x: cx + 55, y: cy + 25 }, { x: cx + 55, y: cy + 100 }], size: 5, isEraser: false },
          { points: [{ x: cx - 40, y: cy + 25 }, { x: cx - 40, y: cy + 85 }], size: 4, isEraser: false },
          { points: [{ x: cx + 40, y: cy + 25 }, { x: cx + 40, y: cy + 85 }], size: 4, isEraser: false },
        ];
      } else if (type === 'table') {
        presetStrokes = [
          // Table top surface
          { points: [{ x: cx - 90, y: cy - 20 }, { x: cx + 90, y: cy - 20 }, { x: cx + 75, y: cy }, { x: cx - 75, y: cy }, { x: cx - 90, y: cy - 20 }], size: 6, isEraser: false },
          // 4 Legs
          { points: [{ x: cx - 80, y: cy }, { x: cx - 80, y: cy + 90 }], size: 5, isEraser: false },
          { points: [{ x: cx + 80, y: cy }, { x: cx + 80, y: cy + 90 }], size: 5, isEraser: false },
          { points: [{ x: cx - 65, y: cy }, { x: cx - 65, y: cy + 75 }], size: 4, isEraser: false },
          { points: [{ x: cx + 65, y: cy }, { x: cx + 65, y: cy + 75 }], size: 4, isEraser: false },
        ];
      } else if (type === 'lamp') {
        presetStrokes = [
          // Shade
          { points: [{ x: cx - 30, y: cy - 80 }, { x: cx + 30, y: cy - 80 }, { x: cx + 55, y: cy - 30 }, { x: cx - 55, y: cy - 30 }, { x: cx - 30, y: cy - 80 }], size: 5, isEraser: false },
          // Stem
          { points: [{ x: cx, y: cy - 30 }, { x: cx, y: cy + 70 }], size: 6, isEraser: false },
          // Base
          { points: [{ x: cx - 45, y: cy + 70 }, { x: cx + 45, y: cy + 70 }, { x: cx + 40, y: cy + 80 }, { x: cx - 40, y: cy + 80 }, { x: cx - 45, y: cy + 70 }], size: 5, isEraser: false },
        ];
      } else if (type === 'mug') {
        presetStrokes = [
          // Cup cylinder
          { points: [{ x: cx - 45, y: cy - 50 }, { x: cx + 45, y: cy - 50 }, { x: cx + 40, y: cy + 50 }, { x: cx - 40, y: cy + 50 }, { x: cx - 45, y: cy - 50 }], size: 5, isEraser: false },
          // Rim ellipse
          { points: [{ x: cx - 45, y: cy - 50 }, { x: cx, y: cy - 40 }, { x: cx + 45, y: cy - 50 }], size: 4, isEraser: false },
          // Handle
          { points: [{ x: cx + 43, y: cy - 30 }, { x: cx + 75, y: cy - 10 }, { x: cx + 75, y: cy + 20 }, { x: cx + 39, y: cy + 35 }], size: 5, isEraser: false },
        ];
      }

      setStrokes(presetStrokes);
      setRedoStack([]);
    };

    useImperativeHandle(ref, () => ({
      getBlob: async (): Promise<Blob | null> => {
        const canvas = canvasRef.current;
        if (!canvas || strokes.length === 0) return null;

        // Render pure clean export without grid lines on standard 512x512
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = 512;
        exportCanvas.height = 512;
        const eCtx = exportCanvas.getContext('2d');
        if (!eCtx) return null;

        const rect = canvas.getBoundingClientRect();
        const scaleX = 512 / rect.width;
        const scaleY = 512 / rect.height;

        eCtx.fillStyle = '#ffffff';
        eCtx.fillRect(0, 0, 512, 512);

        for (const stroke of strokes) {
          if (stroke.points.length < 1) continue;
          eCtx.beginPath();
          eCtx.lineCap = 'round';
          eCtx.lineJoin = 'round';
          eCtx.lineWidth = stroke.size * Math.min(scaleX, scaleY);
          eCtx.strokeStyle = stroke.isEraser ? '#ffffff' : '#000000';

          const p0 = stroke.points[0];
          eCtx.moveTo(p0.x * scaleX, p0.y * scaleY);
          for (let i = 1; i < stroke.points.length; i++) {
            const pt = stroke.points[i];
            eCtx.lineTo(pt.x * scaleX, pt.y * scaleY);
          }
          eCtx.stroke();
        }

        return new Promise<Blob | null>((resolve) => {
          exportCanvas.toBlob((blob) => resolve(blob), 'image/png');
        });
      },
      isEmpty: () => strokes.length === 0,
      clear: handleClear,
      loadPreset: loadPreset,
    }));

    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Toolbar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 12px',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)',
            gap: '8px',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={() => setIsEraser(false)}
              style={{
                background: !isEraser ? 'var(--accent)' : 'var(--bg-input)',
                color: !isEraser ? '#fff' : 'var(--text-muted)',
                borderColor: !isEraser ? 'var(--accent)' : 'var(--border-subtle)',
              }}
              title="Brush Tool"
            >
              Pen
            </button>
            <button
              onClick={() => setIsEraser(true)}
              style={{
                background: isEraser ? 'var(--accent)' : 'var(--bg-input)',
                color: isEraser ? '#fff' : 'var(--text-muted)',
                borderColor: isEraser ? 'var(--accent)' : 'var(--border-subtle)',
              }}
              title="Eraser Tool"
            >
              Eraser
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Size</span>
              <input
                type="range"
                min="2"
                max="20"
                value={brushSize}
                onChange={(e) => setBrushSize(Number(e.target.value))}
                style={{ width: '60px', height: '4px', cursor: 'pointer', padding: 0 }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', width: '16px' }}>{brushSize}</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button onClick={handleUndo} disabled={strokes.length === 0} title="Undo stroke">
              Undo
            </button>
            <button onClick={handleRedo} disabled={redoStack.length === 0} title="Redo stroke">
              Redo
            </button>
            <button onClick={handleClear} disabled={strokes.length === 0} title="Clear canvas">
              Clear
            </button>
          </div>
        </div>

        {/* Canvas drawing container */}
        <div
          style={{
            position: 'relative',
            flex: 1,
            minHeight: '380px',
            background: '#ffffff',
            cursor: isEraser ? 'cell' : 'crosshair',
            overflow: 'hidden',
            touchAction: 'none',
          }}
        >
          <canvas
            ref={canvasRef}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
            style={{
              width: '100%',
              height: '100%',
              display: 'block',
              touchAction: 'none',
            }}
          />
          {strokes.length === 0 && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                pointerEvents: 'none',
                textAlign: 'center',
                color: '#94a3b8',
                userSelect: 'none',
              }}
            >
              <div style={{ fontSize: '13px', fontWeight: 500 }}>Draw a 2D sketch here</div>
              <div style={{ fontSize: '11px', color: '#cbd5e1' }}>Freehand stroke silhouette of your object</div>
            </div>
          )}
        </div>

        {/* Presets footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 12px',
            borderTop: '1px solid var(--border-subtle)',
            background: 'var(--bg-panel)',
            fontSize: '11px',
            color: 'var(--text-dim)',
          }}
        >
          <span>Demo Presets:</span>
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => loadPreset('chair')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Chair
            </button>
            <button
              onClick={() => loadPreset('table')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Table
            </button>
            <button
              onClick={() => loadPreset('lamp')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Lamp
            </button>
            <button
              onClick={() => loadPreset('mug')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Mug
            </button>
          </div>
        </div>
      </div>
    );
  }
);
