import React, { useState } from 'react';
import { RefinementHistoryEntry } from '../types/scene';

interface RefinementInputProps {
  onRefine: (refinementText: string) => void;
  isLoading: boolean;
  disabled: boolean;
  history: RefinementHistoryEntry[];
  currentVersion: number;
  onSelectVersion: (version: number) => void;
}

const REFINEMENT_PRESETS = [
  'Make the backrest taller and add armrests',
  'Make the legs longer and slimmer',
  'Make it wider and more rounded',
  'Add four sturdy support crossbars at the base',
];

export const RefinementInput: React.FC<RefinementInputProps> = ({
  onRefine,
  isLoading,
  disabled,
  history,
  currentVersion,
  onSelectVersion,
}) => {
  const [refinementText, setRefinementText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!refinementText.trim() || disabled || isLoading) return;
    onRefine(refinementText.trim());
    setRefinementText('');
  };

  return (
    <div
      style={{
        background: 'var(--bg-panel)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '4px',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: '12px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--text-muted)',
          }}
        >
          Refine 3D Model
        </span>

        {/* History versions */}
        {history.length > 1 && (
          <div style={{ display: 'flex', gap: '4px' }}>
            {history.map((entry) => (
              <button
                key={entry.version}
                type="button"
                onClick={() => onSelectVersion(entry.version)}
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  background: entry.version === currentVersion ? 'var(--accent)' : 'var(--bg-surface)',
                  color: entry.version === currentVersion ? '#fff' : 'var(--text-muted)',
                  borderColor: entry.version === currentVersion ? 'var(--accent)' : 'var(--border-subtle)',
                }}
              >
                v{entry.version}
              </button>
            ))}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          placeholder="e.g. Make the backrest taller and add armrests"
          value={refinementText}
          onChange={(e) => setRefinementText(e.target.value)}
          disabled={disabled || isLoading}
          style={{ flex: 1, fontSize: '13px' }}
        />
        <button
          type="submit"
          disabled={!refinementText.trim() || disabled || isLoading}
          style={{
            background: 'var(--accent)',
            borderColor: 'var(--accent)',
            color: '#fff',
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          {isLoading ? 'Updating...' : 'Regenerate'}
        </button>
      </form>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', alignItems: 'center' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Suggestions:</span>
        {REFINEMENT_PRESETS.map((p, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled || isLoading}
            onClick={() => setRefinementText(p)}
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              background: 'var(--bg-input)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
};
