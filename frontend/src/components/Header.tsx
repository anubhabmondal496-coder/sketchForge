import React from 'react';
import { HealthResponse } from '../types/scene';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  healthError: string | null;
  onRefreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  healthLoading,
  healthError,
  onRefreshHealth,
}) => {
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-panel)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '32px',
            height: '32px',
            borderRadius: '4px',
            background: 'var(--accent)',
            color: '#fff',
            fontWeight: 800,
            fontSize: '15px',
            letterSpacing: '-0.5px',
          }}
        >
          SF
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <h1 style={{ fontSize: '16px', fontWeight: 700, letterSpacing: '-0.2px', margin: 0 }}>
              SketchForge
            </h1>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              From sketch to geometry
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {health?.mock_mode && (
          <span
            style={{
              padding: '2px 8px',
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              background: '#78350f',
              color: '#fef3c7',
              border: '1px solid #b45309',
              borderRadius: '3px',
            }}
          >
            DEMO / MOCK MODE
          </span>
        )}

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '4px 10px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '4px',
            fontSize: '12px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: healthLoading
                ? 'var(--status-amber)'
                : healthError
                ? 'var(--status-red)'
                : 'var(--status-green)',
            }}
          />
          <span style={{ color: 'var(--text-muted)' }}>
            {healthLoading
              ? 'Checking backend...'
              : healthError
              ? 'Backend offline'
              : health?.gpu
              ? `GPU Active (${health.device})`
              : 'CPU / Mock fallback'}
          </span>
          <button
            type="button"
            onClick={onRefreshHealth}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
            }}
            title="Refresh backend status"
          >
            ↻
          </button>
        </div>
      </div>
    </header>
  );
};
