import React, { useEffect, useState } from 'react';
import { JobStatus } from '../types/scene';

interface GenerationStatusProps {
  jobId?: string | null;
  status: JobStatus | null;
  stageMessage?: string;
  error?: string | null;
  generationTime?: number;
  onDismissError?: () => void;
}

const STAGES = [
  { key: 'queued', label: 'Queued for inference' },
  { key: 'analyzing', label: 'Analyzing sketch with Gemma 4 E4B...' },
  { key: 'generating', label: 'Generating 3D mesh with TripoSR...' },
  { key: 'processing', label: 'Exporting GLB geometry...' },
  { key: 'completed', label: 'Reconstruction completed' },
];

export const GenerationStatus: React.FC<GenerationStatusProps> = ({
  jobId,
  status,
  stageMessage,
  error,
  generationTime,
  onDismissError,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let timer: any = null;
    if (status && status !== 'completed' && status !== 'failed') {
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
    return (
      <div
        style={{
          padding: '10px 14px',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '4px',
          color: '#fca5a5',
          fontSize: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <div>
          <strong style={{ color: '#ef4444' }}>Generation Issue: </strong>
          <span>{error}</span>
        </div>
        {onDismissError && (
          <button
            onClick={onDismissError}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              background: 'transparent',
              borderColor: 'rgba(239, 68, 68, 0.4)',
              color: '#fca5a5',
            }}
          >
            Dismiss
          </button>
        )}
      </div>
    );
  }

  if (!status) return null;

  const currentStageIndex = STAGES.findIndex((s) => s.key === status);
  const isWorking = status !== 'completed' && status !== 'failed';

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
