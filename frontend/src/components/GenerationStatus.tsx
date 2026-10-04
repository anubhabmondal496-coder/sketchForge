import React, { useEffect, useState } from 'react';
import { JobStatus } from '../types/scene';

interface GenerationStatusProps {
  jobId?: string | null;
  status: JobStatus | null;
  stageMessage?: string;
  error?: string | null;
  generationTime?: number;
  onDismissError?: () => void;
  detectedObjects?: string[];
  onSelectObject?: (objectName: string) => void;
}

const STAGES = [
  { key: 'idle', label: 'Draw sketch or upload photo to begin.' },
  { key: 'queued', label: 'Queued for processing' },
  { key: 'analyzing', label: 'Analyzing photo / understanding sketch...' },
  { key: 'searching', label: 'Searching existing 3D assets...' },
  { key: 'found', label: 'Found suitable model.' },
  { key: 'downloading', label: 'Preparing model...' },
  { key: 'importing', label: 'Loading into 3D viewer...' },
  { key: 'generating', label: 'Generating 3D model...' },
  { key: 'processing', label: 'Optimizing geometry...' },
  { key: 'completed', label: 'Model ready.' },
  { key: 'ready', label: 'Model ready.' },
];

export const GenerationStatus: React.FC<GenerationStatusProps> = ({
  jobId,
  status,
  stageMessage,
  error,
  generationTime,
  onDismissError,
  detectedObjects,
  onSelectObject,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let timer: any = null;
    if (status && status !== 'completed' && status !== 'ready' && status !== 'failed' && status !== 'idle') {
      const start = Date.now();
      timer = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - start) / 1000));
      }, 500);
    } else {
      setElapsedSeconds(0);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [status]);

  if (error) {
    const isMultiObjectClarification = error.toLowerCase().includes('multiple objects');

    return (
      <div
        style={{
          padding: '12px 14px',
          background: isMultiObjectClarification ? 'rgba(59, 130, 246, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${isMultiObjectClarification ? 'rgba(59, 130, 246, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          borderRadius: '4px',
          color: isMultiObjectClarification ? '#93c5fd' : '#fca5a5',
          fontSize: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
          <div>
            <strong style={{ color: isMultiObjectClarification ? '#60a5fa' : '#ef4444' }}>
              {isMultiObjectClarification ? 'Clarification Needed: ' : 'Generation Issue: '}
            </strong>
            <span>{error}</span>
          </div>
          {onDismissError && (
            <button
              type="button"
              onClick={onDismissError}
              style={{
                padding: '2px 6px',
                fontSize: '11px',
                background: 'transparent',
                borderColor: isMultiObjectClarification ? 'rgba(59, 130, 246, 0.4)' : 'rgba(239, 68, 68, 0.4)',
                color: isMultiObjectClarification ? '#93c5fd' : '#fca5a5',
              }}
            >
              Dismiss
            </button>
          )}
        </div>

        {/* Multi-object selection buttons */}
        {isMultiObjectClarification && detectedObjects && detectedObjects.length > 0 && onSelectObject && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '2px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', alignSelf: 'center' }}>
              Select target:
            </span>
            {detectedObjects.map((obj) => (
              <button
                key={obj}
                type="button"
                onClick={() => onSelectObject(obj)}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-main)',
                  borderColor: 'var(--border-strong)',
                  fontWeight: 600,
                  textTransform: 'capitalize',
                }}
              >
                Create {obj}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (!status) return null;

  const currentStageIndex = STAGES.findIndex((s) => s.key === status);
  const isWorking = status !== 'completed' && status !== 'ready' && status !== 'failed' && status !== 'idle';

  return (
    <div
      style={{
        padding: '12px 14px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        fontSize: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isWorking ? (
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent)',
                animation: 'pulse 1.2s ease-in-out infinite',
                display: 'inline-block',
              }}
            />
          ) : (
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-green)',
                display: 'inline-block',
              }}
            />
          )}
          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
            {stageMessage || (currentStageIndex >= 0 ? STAGES[currentStageIndex].label : status)}
          </span>
          {jobId && (
            <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              ({jobId.slice(0, 8)})
            </span>
          )}
        </div>

        <span style={{ color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>
          {isWorking ? `${elapsedSeconds}s elapsed` : generationTime ? `${generationTime.toFixed(1)}s` : ''}
        </span>
      </div>

      {/* Functional step indicator */}
      <div style={{ display: 'flex', gap: '4px', height: '4px' }}>
        {STAGES.slice(0, 4).map((stage, idx) => {
          const isActive = idx <= currentStageIndex;
          const isCurrent = idx === currentStageIndex && isWorking;
          return (
            <div
              key={stage.key}
              style={{
                flex: 1,
                background: isCurrent
                  ? 'var(--accent)'
                  : isActive
                  ? 'var(--border-strong)'
                  : 'var(--bg-input)',
                borderRadius: '2px',
                transition: 'background 0.3s ease',
              }}
            />
          );
        })}
      </div>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
};
