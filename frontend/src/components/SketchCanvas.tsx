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

const CANVAS_RES = 800; // Fixed internal bitmap resolution (never mutated, impossible to wipe)

export const SketchCanvas = forwardRef<SketchCanvasHandle, { onStrokeChange?: (hasStrokes: boolean) => void }>(
  ({ onStrokeChange }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    const [isDrawing, setIsDrawing] = useState(false);
    const [brushSize, setBrushSize] = useState<number>(6);
    const [isEraser, setIsEraser] = useState<boolean>(false);
    const [strokes, setStrokes] = useState<Stroke[]>([]);
    const [redoStack, setRedoStack] = useState<Stroke[]>([]);

    const currentStroke = useRef<Stroke | null>(null);
    const strokesRef = useRef<Stroke[]>([]);
    strokesRef.current = strokes;

    // Redraw all strokes cleanly onto the 800x800 bitmap
    const renderCanvas = useCallback(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Fill pure white background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, CANVAS_RES, CANVAS_RES);

      // Draw subtle grid guides
      ctx.strokeStyle = '#f1f5f9';
      ctx.lineWidth = 1.5;
      const gridSize = 40;
      for (let x = gridSize; x < CANVAS_RES; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, CANVAS_RES);
        ctx.stroke();
      }
      for (let y = gridSize; y < CANVAS_RES; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(CANVAS_RES, y);
        ctx.stroke();
      }

      // Combine committed strokes + active in-progress stroke with null-filtering
      const live = currentStroke.current;
      const allStrokes = live && live.points ? [...strokesRef.current, live] : strokesRef.current;

      for (const stroke of allStrokes) {
        if (!stroke || !stroke.points || stroke.points.length === 0) continue;

        ctx.fillStyle = stroke.isEraser ? '#ffffff' : '#111827';
        ctx.strokeStyle = stroke.isEraser ? '#ffffff' : '#111827';
        ctx.lineWidth = stroke.size;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (stroke.points.length === 1) {
          // Single dot
          const p = stroke.points[0];
          if (!p) continue;
          ctx.beginPath();
          ctx.arc(p.x, p.y, stroke.size / 2, 0, Math.PI * 2);
          ctx.fill();
        } else {
          // Continuous stroke
          const startPt = stroke.points[0];
          if (!startPt) continue;
          ctx.beginPath();
          ctx.moveTo(startPt.x, startPt.y);
          for (let i = 1; i < stroke.points.length; i++) {
            const pt = stroke.points[i];
            if (pt) {
              ctx.lineTo(pt.x, pt.y);
            }
          }
          ctx.stroke();
        }
      }
    }, []);

    // Initial render and render on stroke updates
    useEffect(() => {
      renderCanvas();
      onStrokeChange?.(strokes.length > 0);
    }, [strokes, renderCanvas, onStrokeChange]);

    const getPointFromEvent = (e: React.PointerEvent<HTMLCanvasElement>): Point | null => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;

      // Transform client coordinates into fixed 800x800 coordinate space
      const scaleX = CANVAS_RES / rect.width;
      const scaleY = CANVAS_RES / rect.height;

      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    };

    const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      e.stopPropagation();

      const pt = getPointFromEvent(e);
      if (!pt) return;

      try {
        e.currentTarget.setPointerCapture(e.pointerId);
      } catch {
        // Fallback
      }

      setIsDrawing(true);
      currentStroke.current = {
        points: [pt],
        size: brushSize,
        isEraser: isEraser,
      };

      renderCanvas();
    };

    const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawing || !currentStroke.current || !currentStroke.current.points) return;
      e.preventDefault();
      e.stopPropagation();

      const pt = getPointFromEvent(e);
      if (!pt) return;

      currentStroke.current.points.push(pt);
      renderCanvas();
    };

    const handlePointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (!isDrawing) return;
      e.preventDefault();
      e.stopPropagation();

      try {
        if (e.currentTarget.hasPointerCapture(e.pointerId)) {
          e.currentTarget.releasePointerCapture(e.pointerId);
        }
      } catch {
        // Fallback
      }

      setIsDrawing(false);

      const active = currentStroke.current;
      currentStroke.current = null;

      if (active && Array.isArray(active.points) && active.points.length > 0) {
        setStrokes((prev) => [...prev, active]);
        setRedoStack([]);
      }
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
      currentStroke.current = null;
      setStrokes([]);
      setRedoStack([]);
    };

    const loadPreset = (type: 'chair' | 'table' | 'lamp' | 'mug') => {
      const cx = CANVAS_RES / 2;
      const cy = CANVAS_RES / 2;

      let presetStrokes: Stroke[] = [];

      if (type === 'chair') {
        presetStrokes = [
          // Backrest vertical posts
          { points: [{ x: cx - 100, y: cy - 180 }, { x: cx - 100, y: cy + 20 }], size: 8, isEraser: false },
          { points: [{ x: cx + 100, y: cy - 180 }, { x: cx + 100, y: cy + 20 }], size: 8, isEraser: false },
          // Backrest top rail & splats
          { points: [{ x: cx - 105, y: cy - 170 }, { x: cx + 105, y: cy - 170 }], size: 10, isEraser: false },
          { points: [{ x: cx - 50, y: cy - 170 }, { x: cx - 50, y: cy + 20 }], size: 6, isEraser: false },
          { points: [{ x: cx + 50, y: cy - 170 }, { x: cx + 50, y: cy + 20 }], size: 6, isEraser: false },
          // Seat cushion / plane
          { points: [{ x: cx - 120, y: cy + 20 }, { x: cx + 120, y: cy + 20 }, { x: cx + 100, y: cy + 50 }, { x: cx - 100, y: cy + 50 }, { x: cx - 120, y: cy + 20 }], size: 8, isEraser: false },
          // Four legs
          { points: [{ x: cx - 110, y: cy + 50 }, { x: cx - 110, y: cy + 200 }], size: 8, isEraser: false },
          { points: [{ x: cx + 110, y: cy + 50 }, { x: cx + 110, y: cy + 200 }], size: 8, isEraser: false },
          { points: [{ x: cx - 80, y: cy + 50 }, { x: cx - 80, y: cy + 170 }], size: 6, isEraser: false },
          { points: [{ x: cx + 80, y: cy + 50 }, { x: cx + 80, y: cy + 170 }], size: 6, isEraser: false },
        ];
      } else if (type === 'table') {
        presetStrokes = [
          { points: [{ x: cx - 180, y: cy - 40 }, { x: cx + 180, y: cy - 40 }, { x: cx + 150, y: cy }, { x: cx - 150, y: cy }, { x: cx - 180, y: cy - 40 }], size: 10, isEraser: false },
          { points: [{ x: cx - 160, y: cy }, { x: cx - 160, y: cy + 180 }], size: 8, isEraser: false },
          { points: [{ x: cx + 160, y: cy }, { x: cx + 160, y: cy + 180 }], size: 8, isEraser: false },
          { points: [{ x: cx - 130, y: cy }, { x: cx - 130, y: cy + 150 }], size: 6, isEraser: false },
          { points: [{ x: cx + 130, y: cy }, { x: cx + 130, y: cy + 150 }], size: 6, isEraser: false },
        ];
      } else if (type === 'lamp') {
        presetStrokes = [
          { points: [{ x: cx - 60, y: cy - 160 }, { x: cx + 60, y: cy - 160 }, { x: cx + 110, y: cy - 60 }, { x: cx - 110, y: cy - 60 }, { x: cx - 60, y: cy - 160 }], size: 8, isEraser: false },
          { points: [{ x: cx, y: cy - 60 }, { x: cx, y: cy + 140 }], size: 10, isEraser: false },
          { points: [{ x: cx - 90, y: cy + 140 }, { x: cx + 90, y: cy + 140 }, { x: cx + 80, y: cy + 160 }, { x: cx - 80, y: cy + 160 }, { x: cx - 90, y: cy + 140 }], size: 8, isEraser: false },
        ];
      } else if (type === 'mug') {
        presetStrokes = [
          { points: [{ x: cx - 90, y: cy - 100 }, { x: cx + 90, y: cy - 100 }, { x: cx + 80, y: cy + 100 }, { x: cx - 80, y: cy + 100 }, { x: cx - 90, y: cy - 100 }], size: 10, isEraser: false },
          { points: [{ x: cx - 90, y: cy - 100 }, { x: cx, y: cy - 80 }, { x: cx + 90, y: cy - 100 }], size: 6, isEraser: false },
          { points: [{ x: cx + 86, y: cy - 60 }, { x: cx + 150, y: cy - 20 }, { x: cx + 150, y: cy + 40 }, { x: cx + 78, y: cy + 70 }], size: 10, isEraser: false },
        ];
      }

      currentStroke.current = null;
      setStrokes(presetStrokes);
      setRedoStack([]);
    };

    useImperativeHandle(ref, () => ({
      getBlob: async (): Promise<Blob | null> => {
        const canvas = canvasRef.current;
        if (!canvas || strokes.length === 0) return null;

        return new Promise<Blob | null>((resolve) => {
          canvas.toBlob((blob) => resolve(blob), 'image/png');
        });
      },
      isEmpty: () => strokes.length === 0,
      clear: handleClear,
      loadPreset: loadPreset,
    }));

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          overscrollBehavior: 'none',
        }}
        onDragStart={(e) => e.preventDefault()}
      >
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
              type="button"
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
              type="button"
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
                max="30"
                value={brushSize}
                onChange={(e) => setBrushSize(Number(e.target.value))}
                style={{ width: '60px', height: '4px', cursor: 'pointer', padding: 0 }}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', width: '16px' }}>{brushSize}</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              type="button"
              onClick={handleUndo}
              disabled={strokes.length === 0}
              title="Undo stroke"
            >
              Undo
            </button>
            <button
              type="button"
              onClick={handleRedo}
              disabled={redoStack.length === 0}
              title="Redo stroke"
            >
              Redo
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={strokes.length === 0}
              title="Clear canvas"
            >
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
            overscrollBehavior: 'none',
            userSelect: 'none',
            WebkitUserSelect: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onContextMenu={(e) => e.preventDefault()}
          onDragStart={(e) => e.preventDefault()}
        >
          <canvas
            ref={canvasRef}
            width={CANVAS_RES}
            height={CANVAS_RES}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            onContextMenu={(e) => e.preventDefault()}
            onDragStart={(e) => e.preventDefault()}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              display: 'block',
              touchAction: 'none',
              overscrollBehavior: 'none',
              userSelect: 'none',
              WebkitUserSelect: 'none',
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
              type="button"
              onClick={() => loadPreset('chair')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Chair
            </button>
            <button
              type="button"
              onClick={() => loadPreset('table')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Table
            </button>
            <button
              type="button"
              onClick={() => loadPreset('lamp')}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              Lamp
            </button>
            <button
              type="button"
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
