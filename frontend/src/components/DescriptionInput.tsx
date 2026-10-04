import React from 'react';

interface DescriptionInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
  label?: string;
}

const SUGGESTIONS = [
  'A simple wooden chair with four legs and a tall backrest',
  'A modern ceramic tea mug with a rounded handle',
  'A minimalist bedside lamp with cylindrical shade',
  'A solid four-legged dining table with thick wooden surface',
];

export const DescriptionInput: React.FC<DescriptionInputProps> = ({
  value,
  onChange,
  disabled = false,
  placeholder,
  label,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <label
          htmlFor="description-input"
          style={{
            fontSize: '12px',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--text-muted)',
          }}
        >
          {label || 'Describe your object'} <span style={{ fontWeight: 400, color: 'var(--text-dim)' }}>(optional)</span>
        </label>
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            disabled={disabled}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
            }}
          >
            Clear
          </button>
        )}
      </div>

      <textarea
        id="description-input"
        rows={2}
        placeholder={placeholder || 'e.g. wooden chair with four legs and a tall backrest'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        style={{
          width: '100%',
          resize: 'vertical',
          fontSize: '13px',
          lineHeight: '1.4',
          fontFamily: 'inherit',
        }}
      />

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-dim)', alignSelf: 'center' }}>Try:</span>
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onChange(s)}
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              background: 'var(--bg-input)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            {s.split(' ')[1] || 'item'}
          </button>
        ))}
      </div>
    </div>
  );
};
